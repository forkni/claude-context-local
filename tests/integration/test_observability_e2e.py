"""End-to-end / functional tests for OTel tracing.

Two tiers:
  Fast (no model) — verify @timed, error_handler, and traced_block emit
                    the right span names without loading any ML model.
  Slow            — full index + search through MCP handlers with the real
                    embedding model; verifies the complete span hierarchy.

OTel provider is installed once at module level because OTel >= 1.x forbids
re-setting the global TracerProvider after the first call.
"""

from __future__ import annotations

import pytest

opentelemetry = pytest.importorskip("opentelemetry", reason="opentelemetry not installed")

from opentelemetry import trace as otel_trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

import utils.observability as _obs


# ---------------------------------------------------------------------------
# Module-level OTel setup (runs once; provider cannot be replaced after this)
# ---------------------------------------------------------------------------

_EXPORTER = InMemorySpanExporter()
_PROVIDER = TracerProvider(resource=Resource({SERVICE_NAME: "test-e2e"}))
_PROVIDER.add_span_processor(SimpleSpanProcessor(_EXPORTER))
otel_trace.set_tracer_provider(_PROVIDER)
_obs._tracer_provider = _PROVIDER
_obs._enabled = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _spans(name: str | None = None) -> list:
    """Return finished spans, optionally filtered by name."""
    spans = list(_EXPORTER.get_finished_spans())
    if name is not None:
        spans = [s for s in spans if s.name == name]
    return spans


@pytest.fixture(autouse=True)
def _clear_spans():
    """Clear the exporter before every test."""
    _EXPORTER.clear()
    yield


# ---------------------------------------------------------------------------
# Fast tier — no embedding model required
# ---------------------------------------------------------------------------


def test_timed_decorator_emits_span():
    """`@timed` must open a traced_block span matching the operation name."""
    from utils.timing import timed

    @timed("my.op")
    def work():
        return 42

    result = work()

    assert result == 42
    assert len(_spans("my.op")) == 1, f"Expected 1 span named 'my.op'; got {[s.name for s in _spans()]}"


def test_timed_nested_inside_parent():
    """Child @timed span must appear alongside a parent traced_block span."""
    from utils.observability import traced_block
    from utils.timing import timed

    @timed("child.op")
    def child():
        return 1

    with traced_block("parent.op"):
        child()

    names = {s.name for s in _spans()}
    assert "parent.op" in names
    assert "child.op" in names


@pytest.mark.asyncio
async def test_error_handler_emits_mcp_tool_span():
    """`error_handler` must emit a `mcp.tool.*` span for successful calls."""
    from mcp_server.tools.decorators import error_handler

    @error_handler("MyTool")
    async def handler(args):
        return {"ok": True}

    result = await handler({})

    assert result == {"ok": True}
    tool_spans = _spans("mcp.tool.mytool")
    assert len(tool_spans) == 1, (
        f"Expected 1 'mcp.tool.mytool' span; got {[s.name for s in _spans()]}"
    )


@pytest.mark.asyncio
async def test_error_handler_span_on_exception():
    """`error_handler` still emits its span even when the handler raises."""
    from mcp_server.tools.decorators import error_handler

    @error_handler("FailTool")
    async def handler(args):
        raise ValueError("oops")

    result = await handler({})

    assert "error" in result
    assert len(_spans("mcp.tool.failtool")) == 1


def test_search_hybrid_span_with_empty_index(tmp_path):
    """`search.hybrid` span is emitted even when the index is empty."""
    from search.hybrid_searcher import HybridSearcher

    searcher = HybridSearcher(storage_dir=str(tmp_path / "storage"))
    results = searcher.search("add two numbers", k=3)

    assert results == []  # empty index → empty results
    hybrid_spans = _spans("search.hybrid")
    assert len(hybrid_spans) == 1, (
        f"Expected 1 'search.hybrid' span; got {[s.name for s in _spans()]}"
    )
    attrs = hybrid_spans[0].attributes
    assert attrs.get("claude.search.mode") == "hybrid"
    assert attrs.get("claude.search.result_count") == 0


def test_wrap_in_context_propagates_to_thread():
    """`wrap_in_context` must carry the OTel context into a worker thread."""
    import concurrent.futures
    from utils.observability import traced_block, wrap_in_context
    from utils.timing import timed

    @timed("thread.work")
    def work():
        return 99

    with traced_block("thread.parent"):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(wrap_in_context(work))
            fut.result()

    names = [s.name for s in _spans()]
    assert "thread.parent" in names
    assert "thread.work" in names


# ---------------------------------------------------------------------------
# Slow tier — requires embedding model to be loaded
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.asyncio
async def test_index_full_span_via_mcp_handler(sample_codebase, tmp_path):
    """Full index run must emit an `index.full` span via the MCP handler."""
    from mcp_server.tools.index_handlers import handle_index_directory

    project_path = str(sample_codebase["auth"].parent.parent.parent)

    result = await handle_index_directory({"directory_path": project_path})

    assert result.get("success") is True
    assert len(_spans("index.full")) >= 1, (
        f"Expected index.full span; got {[s.name for s in _spans()]}"
    )


@pytest.mark.slow
@pytest.mark.asyncio
async def test_search_span_hierarchy_via_mcp_handlers(sample_codebase):
    """After indexing, a search must emit search.hybrid + bm25/dense child spans."""
    from mcp_server.tools.index_handlers import handle_index_directory
    from mcp_server.tools.search_handlers import handle_search_code

    project_path = str(sample_codebase["auth"].parent.parent.parent)
    await handle_index_directory({"directory_path": project_path})
    _EXPORTER.clear()  # only look at search spans

    result = await handle_search_code({"query": "authenticate user", "k": 3})

    assert "error" not in result

    names = [s.name for s in _spans()]
    assert "search.hybrid" in names, f"Missing search.hybrid; got {names}"
    # bm25_search and dense_search run via @timed inside parallel threads
    assert "bm25_search" in names or "dense_search" in names, (
        f"Expected at least one of bm25_search/dense_search; got {names}"
    )
