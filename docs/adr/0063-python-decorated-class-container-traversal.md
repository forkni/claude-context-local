# Make Python decorated classes container nodes

Status: accepted
Date: 2026-09-05

## Context

`decorated_definition` is splittable (`chunking/language_registry.py:422`) but was not in
`_CONTAINER_NODE_TYPES` (`chunking/languages/base.py:207-209`), so `traverse` chunked the wrapper
node and unconditionally returned before the inner `class_definition` was ever visited
(`base.py:1009`). `@dataclass class Foo: def bar(self): ...` therefore yielded one opaque
`decorated_definition` blob; `bar` never surfaced as its own chunk, was not retrievable by
`search_code`, and produced no class→method `contains` edge.

`721ccde` fixed only half of this: a decorated **method already surfaced as a chunk** (e.g. inside
a plain, undecorated class) got a `parent_chunk_id`. This ADR fixes the other half — the *chunk
shape* — for decorated **classes**: their members were never chunked at all, so the assignment fix
had nothing to attach to. `docs/adr/0038-cpp-only-container-traversal-seam.md` recorded this as
the third instance of the container-traversal bug ADR-0038 fixed for C++ only, and predicted the
naive fix would be wrong; both are confirmed below.

**Measured on this repo** (`git ls-files '*.py'`, excluding `tests/`, 233 files): **76 decorated
classes swallowing 72 methods, 34 of them with ≥1 method**, across **31 files**. Worst offenders:
`ApplicationState` (12 methods, 194 lines), `RelationshipEdge` (7/201), `TraversalPolicy` (6/127),
`ChunkId` (4/60).

## Decision

Add an overridable seam, `_container_traversal_root(node)`, that returns *the node whose children
are container members* rather than reusing `node` itself. `PythonChunker` overrides it so a
`decorated_definition` wrapping a class returns the **inner** `class_definition` node — the
wrapper is still chunked once (its `chunk_id` stays load-bearing for golden references) and
`traverse` descends into the inner class's children directly, without ever chunking the inner
node itself.

```python
# chunking/languages/base.py — default: a node is its own traversal root
# iff its type is in _CONTAINER_NODE_TYPES.
def _container_traversal_root(self, node: Any) -> Any | None:
    if node.type in self._CONTAINER_NODE_TYPES:
        return node
    return None


# chunking/languages/python.py — a decorated class is a container,
# a decorated function is not.
def _container_traversal_root(self, node: Any) -> Any | None:
    if node.type == "decorated_definition":
        for child in node.children:
            if child.type in self._CONTAINER_NODE_TYPES:
                return child
        return None
    return super()._container_traversal_root(node)
```

The container-continuation gate in `base.py` now calls this seam instead of testing
`node.type in self._CONTAINER_NODE_TYPES` directly, and recurses into `container_root.children`
instead of `node.children` — the only place `container_root` can differ from `node` today is this
Python override. The split gate gained a fourth conjunct,
`self._container_traversal_root(node) is None`, so a decorated class larger than
`max_chunk_lines` is not split into `split_block` fragments before ever reaching the container
check (verified no-op today: the two largest decorated classes are 194 and 201 lines, both under
the split threshold; also a no-op for C++, whose split-gate node-type tuple has no
`decorated_definition`).

`multi_language_chunker.py:905`'s parent-registration gate widened from
`chunk_type in ("class", "struct", "union", "namespace")` to also admit `"decorated_definition"`
— a decorated class's `chunk_type` is the raw node type (no `NODE_TYPE_MAP` entry for it, so it
falls through `_map_node_type` unchanged), so without this its members would get `parent_name`
from the new container traversal but `parent_chunk_id` would stay `None`, reproducing the exact
bug ADR-0038 fixed for C++'s `struct_specifier`. Admitting decorated *methods* to the same map is
harmless: `_resolve_parent_chunk_id` filters candidates to enclosing spans, and a decorated
method's span never encloses another chunk (nested functions are not chunked). This also shrinks
that function's last-registered-fallback reach, since large decorated classes no longer split
their span short before registration.

## Reasons for the node-returning design (not a bool)

ADR-0038 sketched the future fix as an `_is_container_node(node)` **predicate** — "is this node,
or a single non-decorator child of it, a container type" — returning `bool`. That shape was
rejected once actually implemented, because the container-continuation gate needs to recurse into
*someone's* `.children`, and for a decorated class that someone is not `node` (the wrapper has no
useful children to recurse into beyond the decorators and the inner class) but the **inner
class**. A bool answer would still require re-deriving which node's children to use at the call
site, duplicating the exact same wrapper-unwrapping logic the predicate had just performed.
Returning the node itself collapses "is this a container" and "whose children are the members"
into one seam, and lets a leaf chunker answer both at once without the base class knowing
anything about decorator wrapper shapes.

## Rejected: the naive fix

Simply adding `"decorated_definition"` to `_CONTAINER_NODE_TYPES` — the one-line fix that worked
for C++'s `struct_specifier` — makes traversal recurse into the **wrapper's own children**, where
the inner `class_definition` is itself splittable and (once the frozenset is widened) already
recognized as a container. It gets chunked *again*, as a duplicate, self-parented class chunk,
verified in-memory before this seam was written:

```
decorated_definition  name='Decorated'     parent=None         lines=4-12
class_definition      name='Decorated'     parent='Decorated'  lines=5-12   <-- duplicate
function_definition   name='dec_cls_meth'  parent='Decorated'  lines=8-12
```

`test_decorated_class_no_duplicate_class_chunk` in `tests/unit/chunking/test_parent_chunk_id.py`
pins this: exactly one chunk named `Host`, `chunk_type == "decorated_definition"`, never
`"class"`.

## Rejected: `metadata["wraps"] = "class"` tagging

An alternative considered was tagging decorated-class metadata with `wraps="class"` in
`python.py::extract_metadata`, then having `multi_language_chunker.py` key its parent-registration
gate off that tag rather than off enclosing-span filtering. More precise in principle, but it
churns `metadata` in the `test_chunker_metadata_parity[py]` snapshot for every decorated chunk
(function *and* class) for no benefit `_resolve_parent_chunk_id`'s existing span filter doesn't
already provide — the span filter alone is sufficient because a decorated method's span never
encloses another chunk. Declined.

## Consequences

- **31 existing `module`-summary chunks change content, not id.** `file_summarizer.py:67`
  (`elif chunk.chunk_type in ("method", "decorated_definition"): ...`) feeds
  `collect_symbol_summary`, whose output is embedded in the synthetic per-file `module` chunk
  (`# Module containing N symbols`, `# Key methods: ...`). Adding ~72 new method chunks changes
  what that summary text says for the 31 files containing an affected decorated class — the
  `module` chunk's id (`<rel>.py:0-0:module:<stem>`) is stable, only its content changes. Measured:
  **zero golds in either `evaluation/golden_dataset.json` or `golden_dataset_expanded.json`
  reference any `:module:` or `:module_preamble:` chunk**, so golden-set exposure is nil. Left
  unfixed — `file_summarizer.py:67` also already tallies a `@dataclass`-decorated class under
  *methods* rather than *classes*, a pre-existing wart, and fixing either is out of scope for this
  change (no measured retrieval need, and changing the module-summary text is itself a
  comparability break independent of this one).
- **No `chunker_version`/`INDEX_VERSION` marker was added.** This is the third instance of the
  pattern [ADR-0037](0037-decline-index-version-bump-for-cpp-parity.md) declined to solve
  generically: the chunker changed, but no `.py` file's content did, so
  `merkle_dag.py`'s content-hash incremental-skip check cannot detect that re-chunking is needed.
  An incremental reindex after this change silently keeps the old, coarser chunks — no error, no
  warning. `incremental=False` (a full reindex) is mandatory to pick this up on an existing index,
  exactly as ADR-0037 already requires for the C++ parity change and ADR-0058's freshness verdict
  does not model chunker-code changes as a input to `index_is_current`.
- **Golden-dataset exposure was re-checked, not assumed.** Golden chunk ids are line-range-stripped
  (`file.py:type:name`), so they survive span growth. Zero golds in either dataset reference a
  method of a decorated class (the corrected counts: 24 `:decorated_definition:` golds in
  `golden_dataset.json`, 36 in `golden_dataset_expanded.json`, of which 7 and 10 respectively are
  decorated *classes* — none of those golden ids point at a method that only exists after this
  change).
- **The base default (`node.type in self._CONTAINER_NODE_TYPES`) is byte-identical** to the
  pre-change behavior for every language except Python — confirmed by the full
  `test_chunker_metadata_parity` snapshot suite, where only `[py].json` moved when the fixture
  gained a `@dataclass class Boxed` with one method.
- **Rust's `impl_item`/`mod_item` and C#'s `namespace_declaration`** (ADR-0038's other two
  deferred instances) can now reuse this same seam trivially if either language ever needs a
  wrapper-node override — today neither does, since neither has a decorator-like wrapper node
  around its container types — but they remain gated on ADR-0038's reopening condition (a real
  project driving the need). This ADR does not reopen or resolve that condition.
- **Retrieval canon.** `evaluation/CANON_20260905_REBASELINE.md` was already stale from `721ccde`
  (the assignment-half fix); this change makes it stale a second time, before a re-pin ever
  happened. Per this change's scope decision, no reindex, benchmark run, or canon re-pin was
  performed here — the eventual re-pin will measure both changes together, not in isolation.

## Verification

- Targeted unit tests: `tests/unit/chunking/test_parent_chunk_id.py` (19 tests, 6 new — duplicate
  chunk guard, span-unchanged guard, decorated-method-inside-decorated-class, decorated-function-
  still-not-a-container, nested-plain-class asymmetry) and one new test in
  `tests/unit/search/test_graph_integration.py::TestClassContainsMethodEdge` (decorated class
  parent, plain method child).
  `tests/unit/chunking/test_multi_language.py` (C++ container precedent, unchanged) reconfirmed
  green.
- `test_chunker_metadata_parity` snapshot re-recorded for `[py]` only, confirmed by
  `git diff --stat` against the snapshot directory.
- Full `tests/unit/chunking/` + `tests/unit/search/` suites, and the whole `tests/unit/` suite,
  pass with no other regressions.
- A read-only, non-committed audit script scanned every git-tracked non-test `.py` file with the
  real `MultiLanguageChunker`: 34 affected classes / 72 methods, zero duplicate-chunk failures,
  zero span regressions, zero unresolved `parent_chunk_id` — matching the measurement above
  exactly. A second script confirmed empirically (not just by reading) that
  `EmbeddingDocumentComposer._get_class_signature`'s existing `chunk_type == "method"` whitelist
  already covers these new chunks, so no change was needed there.
