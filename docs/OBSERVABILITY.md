# Observability

claude-context-local includes opt-in OpenTelemetry (OTel) distributed tracing
across the main pipeline stages. It is **off by default** and has zero overhead
when disabled.

## Installation

```bash
uv pip install -e .[otel]
```

This installs `opentelemetry-api`, `opentelemetry-sdk`, and
`opentelemetry-exporter-otlp-proto-http`. The server runs fine without these
packages — tracing degrades silently to a no-op.

## Enabling tracing

Set `CLAUDE_OTEL_ENABLED=true` before starting the server:

```bash
CLAUDE_OTEL_ENABLED=true python mcp_server/server.py
```

Or add it to your MCP client configuration (`claude_desktop_config.json`):

```json
{
  "env": {
    "CLAUDE_OTEL_ENABLED": "true",
    "CLAUDE_OTEL_EXPORTER": "otlp",
    "CLAUDE_OTEL_ENDPOINT": "http://localhost:4318"
  }
}
```

## Configuration

| Env var | Default | Description |
|---|---|---|
| `CLAUDE_OTEL_ENABLED` | `false` | Enable tracing |
| `CLAUDE_OTEL_EXPORTER` | `otlp` | Exporter: `otlp`, `console`, `none` |
| `CLAUDE_OTEL_ENDPOINT` | `http://localhost:4318` | OTLP HTTP endpoint |
| `CLAUDE_OTEL_SAMPLE` | `1.0` | Sampling ratio (0.0–1.0) |
| `CLAUDE_OTEL_CAPTURE_QUERY` | `false` | Include query text in spans (off by default — queries may be sensitive) |

### Auto-detect

If any standard `OTEL_*` env var is set and `CLAUDE_OTEL_ENABLED` is absent,
the server automatically enables tracing with `exporter=otlp`. This makes
it compatible with standard OTel infrastructure without requiring
project-specific env vars.

## Exporters

### OTLP (recommended)

Sends spans over HTTP to any OTel-compatible collector (Jaeger, Tempo, Grafana,
Honeycomb, Datadog, etc.). Default when enabled.

**Jaeger (quickstart):**

```bash
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 4318:4318 \
  jaegertracing/all-in-one:latest

CLAUDE_OTEL_ENABLED=true python mcp_server/server.py
# Open http://localhost:16686
```

**Grafana Tempo + OTel collector:**

```yaml
# docker-compose.yml excerpt
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib
    ports: ["4318:4318"]
  tempo:
    image: grafana/tempo
```

### Console (stderr)

Prints human-readable span output to **stderr** (never stdout — stdout is the
MCP JSON-RPC channel):

```bash
CLAUDE_OTEL_ENABLED=true CLAUDE_OTEL_EXPORTER=console python mcp_server/server.py 2>traces.log
```

### None

Accepts and silently drops all spans. Useful for testing the OTel code path
without an active collector:

```bash
CLAUDE_OTEL_ENABLED=true CLAUDE_OTEL_EXPORTER=none python mcp_server/server.py
```

## Span hierarchy

```
mcp.tool.<name>                  ← set by error_handler decorator
  index.full                     ← full re-index
    index.incremental            ← incremental update (_add_new_chunks)
  search.hybrid                  ← every search call
    search.embed_query           ← @timed in embedder
    search.bm25                  ← @timed in search_executor (parallel thread)
    search.dense                 ← @timed in search_executor (parallel thread)
    search.multi_hop             ← @timed in multi_hop_searcher
    search.rerank                ← @timed in reranking_engine
```

Thread context is propagated to the parallel bm25/dense workers via
`wrap_in_context`, so their spans nest correctly under `search.hybrid`.

## stdio safety

The MCP server uses stdio transport: stdout is the JSON-RPC stream. The
`console` exporter is always routed to `sys.stderr` to prevent protocol
corruption. The `otlp` exporter (default) uses a network connection and never
touches stdio.

## Overhead

When disabled (default):
- Zero OTel SDK imports at module level.
- `traced_block` returns on a single boolean check.
- Benchmark: <1 µs/call, 100k calls < 100 ms.

When enabled:
- Per-span overhead is the OTel SDK's `BatchSpanProcessor` overhead
  (background thread, non-blocking on the hot path).
- Wall-clock overhead per search query < 5% in benchmarks.

## v2 roadmap

Metrics (counters, histograms, Prometheus endpoint) are deferred to v2.
See ADR-0004 for the decision rationale.
