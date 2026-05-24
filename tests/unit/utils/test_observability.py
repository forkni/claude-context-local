"""Unit tests for utils/observability.py.

Tests cover:
- Disabled noop path (zero SDK imports, zero overhead)
- Enabled path with InMemorySpanExporter
- wrap_in_context propagation
- stdio-safety: console exporter routes to stderr, not stdout
"""

import sys
import time

import pytest


try:
    import opentelemetry  # noqa: F401

    _OTEL_AVAILABLE = True
except ImportError:
    _OTEL_AVAILABLE = False

needs_otel = pytest.mark.skipif(
    not _OTEL_AVAILABLE, reason="opentelemetry not installed"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_in_memory_exporter():
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    return InMemorySpanExporter()


def _reset_observability():
    import utils.observability as obs

    obs._enabled = False
    obs._tracer_provider = None


def _enable_with_in_memory(exporter):
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    import utils.observability as obs

    current = trace.get_tracer_provider()
    if isinstance(current, TracerProvider):
        # A real SDK provider is already set (e.g. by test_observability_e2e at
        # pytest collection time — OTel >= 1.x forbids overriding it).  Add our
        # exporter so spans reach self.exporter in addition to the existing one.
        current.add_span_processor(SimpleSpanProcessor(exporter))
        obs._tracer_provider = current
    else:
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource

        provider = TracerProvider(resource=Resource({SERVICE_NAME: "test"}))
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        obs._tracer_provider = provider
    obs._enabled = True


# ---------------------------------------------------------------------------
# Noop / disabled path — no OTel required
# ---------------------------------------------------------------------------


class TestNoopPath:
    def setup_method(self):
        _reset_observability()

    def teardown_method(self):
        _reset_observability()

    def test_traced_block_disabled_yields_noop_span(self):
        from utils.observability import _NoopSpan, traced_block

        with traced_block("some.span") as span:
            assert isinstance(span, _NoopSpan)

    def test_noop_span_set_attribute_is_silent(self):
        from utils.observability import _NoopSpan

        span = _NoopSpan()
        span.set_attribute("key", "value")  # must not raise

    def test_traced_block_propagates_caller_exception_when_disabled(self):
        from utils.observability import traced_block

        with pytest.raises(ValueError, match="boom"), traced_block("x"):
            raise ValueError("boom")

    def test_wrap_in_context_disabled_returns_fn_unchanged(self):
        from utils.observability import wrap_in_context

        def fn(x):
            return x * 2

        wrapped = wrap_in_context(fn)
        assert wrapped is fn

    def test_is_enabled_false_when_disabled(self):
        from utils.observability import is_enabled

        assert not is_enabled()

    def test_get_tracer_returns_noop_tracer_when_disabled(self):
        from utils.observability import _NoopTracer, get_tracer

        assert isinstance(get_tracer(), _NoopTracer)

    def test_noop_overhead(self):
        """traced_block no-op must be <1 µs/call on average (100k iters < 100 ms)."""
        from utils.observability import traced_block

        iterations = 100_000
        start = time.perf_counter()
        for _ in range(iterations):
            with traced_block("bench"):
                pass
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 100, (
            f"noop overhead too high: {elapsed_ms:.1f}ms for {iterations} iters"
        )


# ---------------------------------------------------------------------------
# Enabled path — requires opentelemetry installed
# ---------------------------------------------------------------------------


@needs_otel
class TestEnabledPath:
    # OTel >= 1.x does not allow re-setting the global TracerProvider.
    # We install it once at class level and just clear() the exporter between tests.

    @classmethod
    def setup_class(cls):
        cls.exporter = _make_in_memory_exporter()
        _enable_with_in_memory(cls.exporter)

    @classmethod
    def teardown_class(cls):
        import utils.observability as obs

        obs._enabled = False
        obs._tracer_provider = None

    def setup_method(self):
        self.exporter.clear()

    def test_traced_block_emits_span(self):
        from utils.observability import traced_block

        with traced_block("test.span"):
            pass

        spans = self.exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "test.span"

    def test_traced_block_sets_attributes(self):
        from utils.observability import traced_block

        with traced_block("test.attrs", mode="hybrid", k=10):
            pass

        spans = self.exporter.get_finished_spans()
        attrs = spans[0].attributes
        assert attrs.get("mode") == "hybrid"
        assert attrs.get("k") == 10

    def test_traced_block_propagates_exception(self):
        from utils.observability import traced_block

        with pytest.raises(RuntimeError, match="expected"), traced_block("err.span"):
            raise RuntimeError("expected")

        spans = self.exporter.get_finished_spans()
        assert len(spans) == 1  # span still recorded

    def test_traced_block_none_attrs_skipped(self):
        from utils.observability import traced_block

        with traced_block("test.none", present="yes", absent=None):
            pass

        spans = self.exporter.get_finished_spans()
        attrs = spans[0].attributes
        assert "present" in attrs
        assert "absent" not in attrs

    def test_is_enabled_true(self):
        from utils.observability import is_enabled

        assert is_enabled()

    def test_nested_spans_parent_child(self):
        from utils.observability import traced_block

        with traced_block("parent"), traced_block("child"):
            pass

        spans = self.exporter.get_finished_spans()
        assert len(spans) == 2
        names = {s.name for s in spans}
        assert names == {"parent", "child"}


# ---------------------------------------------------------------------------
# Stdio safety: console exporter must route to stderr
# ---------------------------------------------------------------------------


@needs_otel
class TestStdioSafety:
    def test_build_exporter_console_uses_stderr(self):
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        from utils.observability import _build_exporter

        class _FakeCfg:
            service_name = "test"
            exporter = "console"
            otlp_endpoint = "http://localhost:4318"
            sample_ratio = 1.0
            capture_query_text = False

        exp = _build_exporter(_FakeCfg(), "console")
        assert isinstance(exp, ConsoleSpanExporter)
        assert exp.out is sys.stderr, (
            "console exporter must write to stderr, not stdout"
        )

    def test_build_exporter_none_returns_noop(self):
        from utils.observability import _build_exporter, _NoopExporter

        class _FakeCfg:
            otlp_endpoint = "http://localhost:4318"

        exp = _build_exporter(_FakeCfg(), "none")
        assert isinstance(exp, _NoopExporter)
