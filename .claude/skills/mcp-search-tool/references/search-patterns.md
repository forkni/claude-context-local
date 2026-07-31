# Search Patterns and Rank Reliability

## Contents

- When Rank-1 Is Reliable
- When You MUST Scan All Results
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
- Queries where module summary chunks may surface (they have `chunk_type="module"` and appear at rank 1-2)

Use `chunk_type="function"` or `chunk_type="class"` to filter out synthetic summary chunks when you need specific implementations.

---

## Query Patterns by Goal

### Finding a Function Definition

```python
code-search:search_code("function description", chunk_type="function")
```

### Finding a Class and Its Methods

```python
# Step 1: Find class
code-search:search_code("ClassName description", chunk_type="class")
# Step 2: Find all methods
code-search:find_connections(chunk_id="...", relationship_types=["defines_class_attr"])
```

### Finding All Callers of a Function

```python
# Step 1: Get chunk_id
results = code-search:search_code("function name", chunk_type="function")
# Step 2: Find callers
code-search:find_connections(chunk_id=results[best]["chunk_id"], relationship_types=["calls"])
```

### Tracing Data Flow Between Components

```python
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

```python
# Get chunk_id of known good implementation
results = code-search:search_code("existing implementation")
# Find similar code
code-search:find_similar_code(chunk_id=results[0]["chunk_id"], k=5)
```

### Searching a Specific Directory

```python
code-search:search_code("query", include_dirs=["src/"])
```

### Exact Symbol Lookup (Fastest)

```python
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

```python
code-search:list_projects      # See all indexed projects
code-search:get_index_status   # Check current project and staleness
code-search:switch_project("path/to/project")  # Switch if needed
```

If index is stale (modified files not reflected):

```python
code-search:index_directory(directory_path="path/to/project", incremental=true)
```
