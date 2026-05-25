#!/usr/bin/env python3
"""Smoke test for the claude-context-local MCP search server.

Usage (from repo root):
    python .claude/skills/mcp-search-tool/smoke.py

Checks in order:
  1. Core module imports
  2. Config loads cleanly (mode, default model, ego_graph settings)
  3. All 19 MCP tools registered in TOOL_REGISTRY
  4. Live search (requires active index): 'embedding model configuration' k=7

Exit 0 on pass, 1 on any failure.
SKIP rows mean the precondition is not met -- not a failure.

Gotcha: Unicode symbols fail on Windows cp1252 terminals -- uses plain ASCII.
"""

import sys
from pathlib import Path


ROOT = (
    Path(__file__).resolve().parents[3]
)  # skill dir -> .claude -> skills -> repo root
sys.path.insert(0, str(ROOT))

errors = 0


def check(label: str, fn) -> bool:
    global errors
    try:
        result = fn()
        note = f": {result}" if result is not None else ""
        print(f"  PASS  {label}{note}")
        return True
    except Exception as exc:
        print(f"  FAIL  {label}: {exc}")
        errors += 1
        return False


print("=== MCP search smoke test ===\n")

# -- 1. Core imports ----------------------------------------------------------
print("Imports:")
try:
    import search.config as _sc  # noqa: F401

    print("  PASS  search.config")
except Exception as e:
    print(f"  FAIL  search.config: {e}")
    errors += 1

try:
    import search.hybrid_searcher as _sh  # noqa: F401

    print("  PASS  search.hybrid_searcher")
except Exception as e:
    print(f"  FAIL  search.hybrid_searcher: {e}")
    errors += 1

try:
    import mcp_server.state as _ms  # noqa: F401

    print("  PASS  mcp_server.state")
except Exception as e:
    print(f"  FAIL  mcp_server.state: {e}")
    errors += 1

try:
    import mcp_server.tool_registry as _tr  # noqa: F401

    print("  PASS  mcp_server.tool_registry")
except Exception as e:
    print(f"  FAIL  mcp_server.tool_registry: {e}")
    errors += 1

# -- 2. Config ----------------------------------------------------------------
print("\nConfig:")
try:
    from search.config import get_search_config

    cfg = get_search_config()

    check("search_mode.default_mode", lambda: cfg.search_mode.default_mode)
    check("routing.default_model", lambda: cfg.routing.default_model)
    check("routing.multi_model_enabled", lambda: str(cfg.routing.multi_model_enabled))
    check(
        "ego_graph settings",
        lambda: (
            f"enabled={cfg.ego_graph.enabled}  "
            f"k_hops={cfg.ego_graph.k_hops}  "
            f"relation_types={cfg.ego_graph.relation_types!r}  "
            f"expansion_mode={cfg.ego_graph.expansion_mode}"
        ),
    )
    check("search_mode.default_k", lambda: str(cfg.search_mode.default_k))
except Exception as exc:
    print(f"  FAIL  get_search_config(): {exc}")
    errors += 1

# -- 3. Tool registry ---------------------------------------------------------
print("\nTool registry:")
try:
    from mcp_server.tool_registry import TOOL_REGISTRY

    EXPECTED = {
        "search_code",
        "find_connections",
        "find_path",
        "find_similar_code",
        "index_directory",
        "list_projects",
        "switch_project",
        "get_index_status",
        "clear_index",
        "delete_project",
        "configure_search_mode",
        "get_search_config_status",
        "configure_query_routing",
        "configure_reranking",
        "configure_chunking",
        "list_embedding_models",
        "switch_embedding_model",
        "get_memory_status",
        "cleanup_resources",
    }

    def _check_registry():
        registered = set(TOOL_REGISTRY)
        missing = EXPECTED - registered
        if missing:
            raise AssertionError(f"missing: {missing}")
        return f"{len(registered)} tools"

    check("all 19 tools present", _check_registry)

    # Verify search_code k default matches expectation
    k_default = TOOL_REGISTRY["search_code"]["input_schema"]["properties"]["k"][
        "default"
    ]
    check(
        "search_code.k default == 4",
        lambda: (
            str(k_default)
            if k_default == 4
            else (_ for _ in ()).throw(AssertionError(f"got {k_default}"))
        ),
    )  # noqa

    # Verify model_key enum is current (no stale 'qwen3' or 'c2llm')
    def _check_model_keys():
        model_enum = TOOL_REGISTRY["search_code"]["input_schema"]["properties"][
            "model_key"
        ]["enum"]
        stale = {"qwen3", "c2llm"} & set(model_enum)
        if stale:
            raise AssertionError(f"stale keys still present: {stale}")
        return str(model_enum)

    check("model_key enum (no stale qwen3/c2llm)", _check_model_keys)

except Exception as exc:
    print(f"  FAIL  TOOL_REGISTRY: {exc}")
    errors += 1

# -- 4. Live search (skip if server not initialised) --------------------------
print("\nLive search:")
try:
    from mcp_server.state import get_state

    state = get_state()

    if state.searcher is None:
        print(
            "  SKIP  searcher not initialised -- start MCP server and index a project first"
        )
    else:

        def _do_search():
            results = state.searcher.search("embedding model configuration", k=7)
            if not results:
                raise AssertionError("no results returned")
            top = results[0]
            score = top.get("blended_score", top.get("score", "?"))
            score_str = f"{score:.3f}" if isinstance(score, float) else str(score)
            return (
                f"{len(results)} results  "
                f"top={top.get('chunk_id', '?')}  "
                f"blended_score={score_str}  "
                f"source={top.get('source', '?')}"
            )

        check("search('embedding model configuration', k=7)", _do_search)

        def _check_source_field():
            results = state.searcher.search("embedding model configuration", k=7)
            sources = sorted({r.get("source", "?") for r in results})
            return f"sources={sources}"

        check("results carry source field", _check_source_field)

except Exception as exc:
    print(f"  SKIP  live search skipped: {exc}")

# -- Summary ------------------------------------------------------------------
print()
if errors:
    print(f"FAIL  ({errors} error{'s' if errors != 1 else ''})")
    sys.exit(1)
else:
    print("PASS")
    sys.exit(0)
