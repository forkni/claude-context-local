"""Unit tests for evaluation.tracer.collector against tests/fixtures/tracer_pkg."""

from __future__ import annotations

import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from evaluation.tracer.collector import (
    EXTERNAL,
    PROJECT,
    TEST,
    Endpoint,
    TraceCollector,
    body_line_of,
)
from tests.fixtures.tracer_pkg import basic, tricky


FIXTURES_ROOT = Path(__file__).resolve().parents[3] / "fixtures"
BASIC = "tracer_pkg/basic.py"
TRICKY = "tracer_pkg/tricky.py"


@contextmanager
def traced(**kwargs) -> Iterator[TraceCollector]:
    collector = TraceCollector(FIXTURES_ROOT, test_dirs=(), **kwargs)
    collector.install()
    try:
        yield collector
    finally:
        collector.uninstall()


def qual_edges(collector: TraceCollector) -> set[tuple[str, str, int]]:
    return {(c.qual, k.qual, d) for (c, k, d) in collector.edges}


def line_of(path: Path, needle: str) -> int:
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if needle in line:
            return i
    raise AssertionError(f"{needle!r} not found in {path}")


# ---------------------------------------------------------------------------
# classification
# ---------------------------------------------------------------------------


def test_classify_project_test_external() -> None:
    collector = TraceCollector(FIXTURES_ROOT.parent, test_dirs=("unit",))
    kind, ep = collector.classify(basic.leaf.__code__)
    assert kind == PROJECT
    assert ep == Endpoint(
        "fixtures/tracer_pkg/basic.py", ep.def_line, ep.body_line, "leaf"
    )
    kind, ep = collector.classify(test_classify_project_test_external.__code__)
    assert kind == TEST
    assert ep is not None and ep.path.startswith("unit/evaluation/tracer/")
    assert collector.classify(Path.read_text.__code__) == (EXTERNAL, None)


def test_classify_is_memoized_per_code_object() -> None:
    collector = TraceCollector(FIXTURES_ROOT, test_dirs=())
    first = collector.classify(basic.leaf.__code__)
    second = collector.classify(basic.leaf.__code__)
    assert first is second
    assert collector.to_payload()["counters"]["classified_code_objects"] == 1


def test_body_line_rules() -> None:
    src = FIXTURES_ROOT / TRICKY
    # Decorated def: co_firstlineno is the decorator line, body_line the first statement.
    # deco() does not use functools.wraps; reach the inner function via the closure.
    code = tricky.decorated.__closure__[0].cell_contents.__code__
    assert code.co_firstlineno == line_of(src, "@deco")
    assert body_line_of(code) == line_of(src, "return leaf(x)")
    # Multi-line signature: body is several lines below the def line.
    code = tricky.multi_line_sig.__code__
    assert code.co_firstlineno == line_of(src, "def multi_line_sig(")
    assert body_line_of(code) == line_of(src, "return leaf(a + b)")
    assert body_line_of(code) > code.co_firstlineno + 3


# ---------------------------------------------------------------------------
# edges: basic constructs
# ---------------------------------------------------------------------------


def test_basic_edges_exact_set() -> None:
    with traced() as collector:
        basic.plain_caller(1)
        basic.instantiate()
        basic.recurse(3)
        basic.comprehension()
        basic.closure_user()
        basic.sort_with_key()
        basic.consume_gen_twice()
    assert collector.handler_errors == 0
    assert qual_edges(collector) == {
        ("plain_caller", "leaf", 0),
        ("instantiate", "Widget.__init__", 0),
        ("Widget.__init__", "leaf", 0),
        ("instantiate", "Widget.method", 0),
        ("Widget.method", "leaf", 0),
        ("recurse", "recurse", 0),
        ("comprehension", "comprehension.<locals>.<listcomp>", 0),
        ("comprehension.<locals>.<listcomp>", "leaf", 0),
        ("closure_user", "closure_user.<locals>.inner", 0),
        ("closure_user.<locals>.inner", "leaf", 0),
        # sorted() is C: the lambda's f_back is sort_with_key itself.
        ("sort_with_key", "sort_with_key.<locals>.<lambda>", 0),
        ("sort_with_key.<locals>.<lambda>", "leaf", 0),
        ("consume_gen_twice", "gen", 0),
        ("gen", "leaf", 0),
    }
    assert all(c.path == BASIC and k.path == BASIC for c, k, _ in collector.edges)


def test_counts_recursion_and_generator_resumption() -> None:
    with traced() as collector:
        basic.recurse(3)
        basic.consume_gen_twice()
    by_qual = {(c.qual, k.qual): n for (c, k, _), n in collector.edges.items()}
    assert collector.self_loops == 3
    assert by_qual[("recurse", "recurse")] == 3
    # Each list(gen()) resumes the generator 3 times (2 yields + StopIteration).
    assert by_qual[("consume_gen_twice", "gen")] == 6
    assert by_qual[("gen", "leaf")] == 4


def test_calls_from_outside_root_are_rootless() -> None:
    with traced() as collector:
        basic.leaf(1)
    assert collector.rootless == 1
    assert collector.edges == {}
    assert collector.hits == {
        Endpoint(
            BASIC,
            basic.leaf.__code__.co_firstlineno,
            body_line_of(basic.leaf.__code__),
            "leaf",
        ): 1
    }


# ---------------------------------------------------------------------------
# edges: tricky constructs
# ---------------------------------------------------------------------------


def test_decorator_wrapper_is_routed_through_locals_wrapper() -> None:
    with traced() as collector:
        tricky.call_decorated()
    assert qual_edges(collector) == {
        ("call_decorated", "deco.<locals>.wrapper", 0),
        ("deco.<locals>.wrapper", "decorated", 0),
        ("decorated", "leaf", 0),
    }


def test_exception_unwinding_keeps_edges() -> None:
    with traced() as collector:
        assert tricky.catcher() == 1
    assert qual_edges(collector) == {
        ("catcher", "middle", 0),
        ("middle", "raiser", 0),
        ("catcher", "leaf", 0),
    }


def test_python_level_external_frame_counts_as_depth_one() -> None:
    with traced() as collector:
        assert tricky.via_external() == 4
    edges = qual_edges(collector)
    assert ("via_external", "managed", 1) in edges  # contextlib.__enter__ in between
    assert ("managed", "leaf", 0) in edges


def test_thread_started_after_install_is_observed_but_rootless() -> None:
    with traced() as collector:
        tricky.run_thread()
    assert len(collector.observed_threads) == 2
    assert collector.rootless >= 1
    assert ("thread_target", "leaf", 0) in qual_edges(collector)
    assert not any(k.qual == "thread_target" for _, k, _ in collector.edges)


def test_dataclass_generated_init_is_invisible() -> None:
    with traced() as collector:
        tricky.make_point()
    assert collector.edges == {}
    assert [ep.qual for ep in collector.hits] == ["make_point"]


def test_module_frames_are_transparent(tmp_path: Path) -> None:
    mod = tmp_path / "pkg_mod.py"
    mod.write_text(
        "from tests.fixtures.tracer_pkg.basic import leaf\nVALUE = leaf(10)\n",
        encoding="utf-8",
    )
    with traced() as collector:
        code = compile(mod.read_text(encoding="utf-8"), str(mod), "exec")
        exec(code, {"__name__": "pkg_mod"})  # noqa: S102 - fixture module body
    # <module> is external, so leaf's caller walk continues past it to the test frame.
    assert collector.edges == {}
    assert [ep.qual for ep in collector.hits] == ["leaf"]


# ---------------------------------------------------------------------------
# test-caller recording, install/uninstall, payload
# ---------------------------------------------------------------------------


def test_record_test_callers_flag() -> None:
    root = FIXTURES_ROOT.parent  # tests/
    off = TraceCollector(root, test_dirs=("unit",))
    off.install()
    try:
        basic.plain_caller(1)
    finally:
        off.uninstall()
    assert off.test_edges == {}

    on = TraceCollector(root, test_dirs=("unit",), record_test_callers=True)
    on.install()
    try:
        basic.plain_caller(1)
    finally:
        on.uninstall()
    (key,) = on.test_edges
    test_path, test_qual, callee = key
    assert test_path == "unit/evaluation/tracer/test_collector.py"
    assert test_qual == "test_record_test_callers_flag"
    assert callee.qual == "plain_caller"
    # The project-to-project edge is still recorded independently.
    assert ("plain_caller", "leaf", 0) in qual_edges(on)


def test_install_and_uninstall_restore_previous_profiler() -> None:
    previous = sys.getprofile()
    previous_thread = getattr(threading, "_profile_hook", None)
    collector = TraceCollector(FIXTURES_ROOT, test_dirs=())
    collector.install()
    assert sys.getprofile() == collector.profile
    assert threading._profile_hook == collector.profile
    assert collector.installed
    collector.install()  # idempotent
    collector.uninstall()
    assert sys.getprofile() is previous
    assert threading._profile_hook is previous_thread
    assert not collector.installed
    collector.uninstall()  # idempotent
    assert collector.preexisting_threads >= 1


def test_handler_error_is_counted_not_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    collector = TraceCollector(FIXTURES_ROOT, test_dirs=())

    def boom(_code):
        raise RuntimeError("classification failed")

    monkeypatch.setattr(collector, "classify", boom)
    collector.install()
    try:
        basic.leaf(1)
    finally:
        collector.uninstall()
    assert collector.handler_errors >= 1
    assert collector.edges == {}


def test_payload_is_sorted_and_index_consistent() -> None:
    with traced(record_test_callers=False) as collector:
        basic.instantiate()
        tricky.call_decorated()
    payload = collector.to_payload()
    assert payload["schema"] == "callgraph-trace-raw/1"
    nodes = payload["nodes"]
    keys = [(n["path"], n["def_line"], n["qual"]) for n in nodes]
    assert keys == sorted(keys)
    assert payload["edges"] == sorted(payload["edges"])
    for caller_idx, callee_idx, depth, count in payload["edges"]:
        assert 0 <= caller_idx < len(nodes) and 0 <= callee_idx < len(nodes)
        assert depth == 0 and count >= 1
    by_qual = {n["qual"]: n for n in nodes}
    assert by_qual["leaf"]["hits"] == 3
    assert by_qual["decorated"]["def_line"] == line_of(FIXTURES_ROOT / TRICKY, "@deco")
    assert payload["counters"]["handler_errors"] == 0
    assert payload["counters"]["call_events"] > len(payload["edges"])
    # Same trace twice gives the same payload (determinism at the collector level).
    with traced() as again:
        basic.instantiate()
        tricky.call_decorated()
    again_payload = again.to_payload()
    for field in ("nodes", "edges", "test_edges"):
        assert again_payload[field] == payload[field]
