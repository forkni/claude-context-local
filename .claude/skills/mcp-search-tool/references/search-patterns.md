# Search Patterns and Rank Reliability

## Contents

- When Rank-1 Is Reliable
- When You MUST Scan All Results
- Two Behaviors Worth Knowing (before you budget context or filter results)
- Query Patterns by Goal (definition, class, callers, flow, similar, directory, exact)
- Search Mode Selection (auto, hybrid, semantic, bm25)
- Project Context Check

## When Rank-1 Is Reliable

Use the top result directly for:

- Small function discovery: "get X", "validate Y", "normalize Z"
- Exact symbol lookup via `chunk_id` parameter
- Unique, specific function names

## When You MUST Scan All Results

Scan all k results for:

- Class overview queries: "what does X do", "how does X work"
- Sibling context queries: "encode and decode", "save and load"
- Queries where module summary chunks matter — under the default ordering (`source_order_output=false`, v0.18.0+) they are demoted to the **tail** of
  the array for non-GLOBAL queries, not rank 1-2, so a low array position does not mean low relevance (`chunk_type="module"`)

Use `chunk_type="function"` or `chunk_type="class"` to filter out synthetic summary chunks when you need specific implementations.

---

## Two Behaviors Worth Knowing

Both of these change how you should budget context and read results. Full detail (with citations) is in `SKILL.md`'s Gotchas table — this is a
pointer, not a duplicate.

- **`k` is not the result count.** Multi-hop/graph-hop/ego-graph expansion (all always-on) adds rows *after* `k` is applied, so a search can return
  several times more rows than `k`. Size context budgets off the actual response length, not off `k`.
- **`relationship_types` on `find_connections` filters only some response sections.** `direct_callers`, `indirect_callers`, `direct_callees`, and
  `similar_code` come back unfiltered regardless of what you pass; only sections like `uses_types`/`exceptions_caught`/`instantiates` are actually
  narrowed by it.

---

## Query Patterns by Goal

### Finding a Function Definition

```text
code-search:search_code("function description", chunk_type="function")
```

### Finding a Class and Its Methods

**There is no structural "list a class's methods" primitive in this toolset.** Two plausible-looking approaches both fail: `find_connections`
with `relationship_types=["defines_class_attr"]` finds `class Foo: attr = value` assignments, not method definitions, and never returns methods.
A direct `search_code(chunk_id=<class chunk_id>)` lookup returns `source: "direct_lookup"` plus a `graph` summary object — also not a method list.

**Reliable route:** find the class, then read the file over the line span its `chunk_id` already encodes.

```text
# Step 1: Find the class — the chunk_id encodes its full line span
results = code-search:search_code("ClassName description", chunk_type="class")
# chunk_id format is file.py:start-end:type:name, e.g. search/ego_graph_retriever.py:29-476:class:EgoGraphRetriever

# Step 2: Read the file over that span with the Read tool — this is the actual method list
```

**Heuristic-only fallback:** `find_similar_code(chunk_id=<class chunk_id>)` often surfaces sibling methods, but by embedding similarity, not
containment — it can miss methods and can surface unrelated similar code. Use it as a supplementary signal, not as the answer.

### Finding All Callers of a Function

```text
# Step 1: Get chunk_id
results = code-search:search_code("function name", chunk_type="function")
# Step 2: Find callers
code-search:find_connections(chunk_id=results[best]["chunk_id"], relationship_types=["calls"])
```

### Tracing Data Flow Between Components

```text
# Find both endpoints first
source = code-search:search_code("source component")
target = code-search:search_code("target component")
# Trace the path
code-search:find_path(
    source_chunk_id=source[0]["chunk_id"],
    target_chunk_id=target[0]["chunk_id"]
)
```

### Finding Similar Implementations

```text
# Get chunk_id of known good implementation
results = code-search:search_code("existing implementation")
# Find similar code
code-search:find_similar_code(chunk_id=results[0]["chunk_id"], k=5)
```

### Searching a Specific Directory

```text
code-search:search_code("query", include_dirs=["src/"])
```

### Exact Symbol Lookup (Fastest)

```text
# If you have the exact chunk_id from a previous search:
code-search:search_code(chunk_id="pipeline.py:100-150:method:forward")
```

---

## Search Mode Selection

| Mode | Best For |
|------|---------|
| `auto` (default) | Most queries — routes intelligently |
| `hybrid` | Conceptual + exact combined |
| `semantic` | Concept/intent queries |
| `bm25` | Exact symbol names, API calls |

For exact function/class names: use `search_mode="bm25"` for fastest results. (Per-mode latency
figures previously shown here were uncorroborated and far below every measured end-to-end run —
see [performance.md](performance.md) for real measured latency.)

---

## Project Context Check

Before searching, verify the correct project is active:

```text
code-search:list_projects      # See all indexed projects
code-search:get_index_status   # Check current project and staleness
code-search:switch_project("path/to/project")  # Switch if needed
```

If index is stale (modified files not reflected):

```text
code-search:index_directory(directory_path="path/to/project", incremental=true)
```
