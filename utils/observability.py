"""Lazy-initialized OTel tracing utilities.

Zero overhead when disabled:
- `traced_block` early-returns on one boolean check when disabled.
- The OTel SDK is only imported inside `init_observability()`.
- `ImportError` for opentelemetry downgrades silently to no-op.

`@timed` in utils/timing.py calls `traced_block`, so all five timed
sites pick up spans for free when tracing is enabled.

Console exporter always routes to stderr to avoid corrupting the MCP
stdio protocol channel (stdout).
"""

from __future__ import annotations

import contextlib
import logging
import os
import sys
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from search.config import ObservabilityConfig


logger = logging.getLogger(__name__)

_enabled: bool = False
_tracer_provider: Any = None  # opentelemetry.sdk.trace.TracerProvider | None


# ---------------------------------------------------------------------------
# No-op stubs (used when disabled or when opentelemetry is not installed)
# ---------------------------------------------------------------------------


class _NoopSpan:
    """Lightweight no-op span returned when tracing is disabled."""

    def set_attribute(self, key: str, value: object) -> None:  # noqa: ARG002
        pass

    def __enter__(self) -> _NoopSpan:
        return self

    def __exit__(self, *args: object) -> None:
        pass


class _NoopTracer:
    def start_as_current_span(self, name: str, **kwargs: Any) -> _NoopSpan:  # noqa: ARG002
        return _NoopSpan()

    def start_span(self, name: str, **kwargs: Any) -> _NoopSpan:  # noqa: ARG002
        return _NoopSpan()


class _NoopExporter:
    def export(self, spans: Any) -> Any:
        try:
            from opentelemetry.sdk.trace.export import (  # pyrefly: ignore [missing-import]
                SpanExportResult,
            )

            return SpanExportResult.SUCCESS
        except ImportError:
            return None

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def is_enabled() -> bool:
    """Return True if tracing is currently active."""
    return _enabled


def force_flush(timeout_millis: int = 30000) -> bool:
    """Flush pending spans without shutting down the tracer provider.

    Respects ADR-0004: never calls shutdown_observability(); shutdown belongs
    at server exit only.  No-op (returns True) when tracing is disabled.
    """
    if not _enabled or _tracer_provider is None:
        return True
    try:
        return bool(_tracer_provider.force_flush(timeout_millis))
    except Exception as exc:  # noqa: BLE001 - resilience: flush is best-effort, never blocks caller
        logger.debug(f"[OTEL] force_flush error (ignored): {exc}")
        return False


def get_tracer(name: str = "claude-context-local") -> Any:
    """Return the active OTel tracer, or a no-op tracer when disabled."""
    if not _enabled or _tracer_provider is None:
        return _NoopTracer()
    try:
        from opentelemetry import trace  # pyrefly: ignore [missing-import]

        return trace.get_tracer(name)
    except Exception:  # noqa: BLE001 - resilience: fall back to no-op tracer when OTel unavailable
        return _NoopTracer()


@contextmanager
def traced_block(name: str, **attrs: Any) -> Generator[Any, None, None]:
    """Open an OTel span covering the block; yield a no-op span when disabled.

    Usage::

        with traced_block("search.hybrid", mode="hybrid", k=10) as span:
            span.set_attribute("result_count", len(results))
            ...
    """
    if not _enabled:
        yield _NoopSpan()
        return

    # Separate setup (safe to catch) from the yield (must propagate caller exceptions).
    try:
        from opentelemetry import trace  # pyrefly: ignore [missing-import]

        tracer = trace.get_tracer("claude-context-local")
    except Exception:  # noqa: BLE001 - resilience: fall back to no-op span when OTel setup fails
        yield _NoopSpan()
        return

    # Yield inside the OTel span; caller exceptions propagate through start_as_current_span.
    with tracer.start_as_current_span(name) as span:
        for k, v in attrs.items():
            if v is not None:
                with contextlib.suppress(Exception):
                    span.set_attribute(k, v)
        yield span


def wrap_in_context(fn: Any) -> Any:
    """Wrap a callable to carry the current OTel context into a worker thread.

    Call this before submitting work to a ThreadPoolExecutor so that child
    spans nest correctly under the parent search span::

        future = executor.submit(wrap_in_context(self._bm25_search), query, k)
    """
    if not _enabled:
        return fn

    try:
        from opentelemetry import (  # pyrefly: ignore [missing-import]
            context as otel_context,
        )

        ctx = otel_context.get_current()

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            token = otel_context.attach(ctx)
            try:
                return fn(*args, **kwargs)
            finally:
                otel_context.detach(token)

        return wrapper
    except Exception:  # noqa: BLE001 - resilience: skip context propagation when OTel unavailable
        return fn


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def init_observability(cfg: ObservabilityConfig) -> None:
    """Initialize OTel tracing from config. Call once at server startup.

    Safe to call multiple times; subsequent calls after successful init are
    no-ops. Degrades gracefully: ImportError → no-op + one WARN.

    The console exporter is always routed to stderr to avoid corrupting
    the MCP stdio protocol channel (stdout is the JSON-RPC stream).
    """
    global _enabled, _tracer_provider

    if _enabled:
        return  # already initialized

    effective_enabled = cfg.enabled
    effective_exporter = cfg.exporter

    # Auto-detect: if any standard OTEL_* env var is set and CLAUDE_OTEL_ENABLED
    # is absent, treat as enabled with OTLP (network — never touches stdio).
    if (
        not effective_enabled
        and "CLAUDE_OTEL_ENABLED" not in os.environ
        and any(k.startswith("OTEL_") for k in os.environ)
    ):
        effective_enabled = True
        effective_exporter = "otlp"
        logger.info(
            "[OTEL] Auto-detected OTEL_* env vars — enabling tracing with OTLP exporter"
        )

    if not effective_enabled:
        return

    try:
        from opentelemetry import trace  # pyrefly: ignore [missing-import]
        from opentelemetry.sdk.resources import (  # pyrefly: ignore [missing-import]
            SERVICE_NAME,
            Resource,
        )
        from opentelemetry.sdk.trace import (  # pyrefly: ignore [missing-import]
            TracerProvider,
        )
        from opentelemetry.sdk.trace.export import (  # pyrefly: ignore [missing-import]
            BatchSpanProcessor,
        )

        resource = Resource(attributes={SERVICE_NAME: cfg.service_name})

        if cfg.sample_ratio < 1.0:
            from opentelemetry.sdk.trace.sampling import (  # pyrefly: ignore [missing-import]
                TraceIdRatioBased,
            )

            provider = TracerProvider(
                resource=resource,
                sampler=TraceIdRatioBased(cfg.sample_ratio),
            )
        else:
            provider = TracerProvider(resource=resource)

        exporter = _build_exporter(cfg, effective_exporter)
        provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)
        _tracer_provider = provider
        _enabled = True

        logger.info(
            f"[OTEL] Tracing enabled: service={cfg.service_name!r}, "
            f"exporter={effective_exporter!r}, sample_ratio={cfg.sample_ratio}"
        )

    except ImportError:
        logger.warning(
            "[OTEL] opentelemetry not installed — tracing disabled. "
            "Install with: pip install 'claude-context-local[otel]'"
        )
    except Exception as exc:  # noqa: BLE001 - resilience: tracing init must never block server startup
        logger.warning(
            f"[OTEL] Failed to initialize tracing: {exc} — continuing without",
            exc_info=True,
        )


def _build_exporter(cfg: ObservabilityConfig, exporter_name: str) -> Any:
    """Build the configured span exporter."""
    name = exporter_name.lower()

    if name == "console":
        from opentelemetry.sdk.trace.export import (  # pyrefly: ignore [missing-import]
            ConsoleSpanExporter,
        )

        # Always stderr — stdout is the MCP stdio protocol channel.
        return ConsoleSpanExporter(out=sys.stderr)

    if name == "otlp":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # pyrefly: ignore [missing-import]
            OTLPSpanExporter,
        )

        return OTLPSpanExporter(endpoint=f"{cfg.otlp_endpoint}/v1/traces")

    # "none" or any unknown value → drop spans silently.
    return _NoopExporter()


def shutdown_observability() -> None:
    """Flush pending spans and shut down the tracer provider.

    Call at server shutdown, after the last request is handled.
    """
    global _enabled, _tracer_provider
    if _tracer_provider is not None:
        try:
            _tracer_provider.shutdown()
        except Exception as exc:  # noqa: BLE001 - cleanup: best-effort provider shutdown, must not block exit
            logger.debug(f"[OTEL] Shutdown error (ignored): {exc}")
        _tracer_provider = None
    _enabled = False
