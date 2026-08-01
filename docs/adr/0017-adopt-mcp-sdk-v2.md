# Adopt MCP Python SDK v2

Status: accepted
Date: 2026-08-01

## Context

`mcp_server/server.py` was built against the v1 low-level SDK (`mcp>=1.28.1,<2`), which wires
each JSON-RPC method to a handler via a decorator applied after construction:
`@server.list_tools()`, `@server.call_tool()`, `@server.list_resources()`,
`@server.read_resource()`, `@server.list_prompts()`, `@server.get_prompt()`. SDK v2 removes
these decorator methods from `mcp.server.lowlevel.Server` entirely — confirmed by reading the
real `mcp-2.0.0` wheel source (`mcp/server/lowlevel/server.py`), which has no `list_tools`,
`call_tool`, `list_resources`, `read_resource`, `list_prompts`, or `get_prompt` methods.
Registration moves to constructor kwargs (`on_list_tools=`, `on_call_tool=`, etc.), so every
handler must exist before `Server(...)` is constructed rather than after. `ADR-0016` removed the
DSPy eval subsystem first specifically to shrink this migration to one file: with
`utils/dspy_mcp.py` gone, `mcp_server/server.py` is the repo's only consumer of the `mcp`
package, server-side only — no client-session (`ClientSession`/`streamablehttp_client`) API to
port alongside it.

Two upstream renames go with the decorator change: `Tool.inputSchema` → `Tool.input_schema`,
`CallToolResult.structuredContent`/`.isError` → `.structured_content`/`.is_error`,
`Resource.mimeType` → `.mime_type` (confirmed against `mcp_types-2.0.0`'s `_types.py`). These
are Python-attribute renames only — pydantic still serializes the wire form in camelCase via
`populate_by_name` aliases, so JSON-RPC consumers see no change.

## Decision

Bump the `mcp` pin to `>=2,<3` and rewrite `mcp_server/server.py`'s six handlers from
`@server.*()`-decorated free functions to plain `async def` functions with the uniform v2
signature `(ctx: ServerRequestContext, params: <ParamsType> | None) -> <ResultType>`, registered
via `Server(..., on_list_tools=handle_list_tools, on_call_tool=handle_call_tool, ...)` after all
six are defined. Convert bare-value returns (`list[Tool]`, raw `str`) to the corresponding
typed result wrapper (`ListToolsResult(tools=...)`, `ReadResourceResult(contents=[...])`, etc.).
Rename the three renamed fields at their two call sites (`tool_registry.py`'s
`Tool(input_schema=...)`, `handle_call_tool`'s `CallToolResult(structured_content=...,
is_error=...)`, `handle_list_resources`'s `Resource(mime_type=...)`). Replace the v1
`raise ValueError(...)` unknown-prompt branch with `raise MCPError(INVALID_PARAMS, ...)` — v2's
dispatch layer expects `mcp.shared.exceptions.MCPError`, not a bare `ValueError`, to produce a
correct JSON-RPC error response.

## Reasons

**`ctx: ServerRequestContext` is accepted but unused by every handler.** Read the full
`ServerRequestContext` dataclass (`mcp/server/context.py`) before writing a single handler: its
fields (`session`, `lifespan_context`, `protocol_version`, `method`, `params`, `request_id`,
`meta`, `request`, `close_sse_stream`, `close_standalone_sse_stream`) offer nothing any of the
six handlers need — none of them touched a session or lifespan object under v1 either. Adding it
as an ignored positional parameter is the correct, minimal port; this repo's ruff config doesn't
enable `ARG` (unused-argument) rules, and `app_lifespan(app: Any)` already has an unused
parameter at the same precedent level.

**`from mcp.types import ...` needs no rewrite.** v2's `mcp/types/__init__.py` does
`from mcp_types import *` and self-documents as a compat shim "so SDK users can keep the
familiar v1 spelling." Every existing import in `mcp_server/server.py` keeps working; only the
new v2-only names (`ListToolsResult`, `ListResourcesResult`, `ReadResourceResult`,
`ListPromptsResult`, `TextResourceContents`, `CallToolRequestParams`, `GetPromptRequestParams`,
`ReadResourceRequestParams`, `PaginatedRequestParams`, `INVALID_PARAMS`) needed adding to the
import list — no existing name needed touching.

**The wire format is unchanged — verified end-to-end, not just by reading source.** After the
rewrite, three independent transports were exercised against the live migrated server: (1) the
HTTP transport directly via `curl` (`initialize` → `notifications/initialized` → `tools/list` →
`tools/call get_index_status`, full JSON-RPC round trip); (2) the real `code-search` MCP client
in this Claude Code session (`get_index_status` + `search_code`, both against the actual
non-mock stdio-equivalent HTTP connection); (3) `code-search-extension/server/index.js`, the
Chrome-extension's dependency-free stdio↔StreamableHTTP bridge, piped two JSON-RPC lines
directly. All three show `Tool.input_schema`/`Resource.mime_type`/`CallToolResult.is_error`
serializing to `inputSchema`/`mimeType`/`isError` on the wire, confirming the pydantic aliases
hold and the extension's raw-JSON-RPC bridge needs no changes.

**`opentelemetry-api` becomes a hard transitive dependency, but does not double-instrument.**
`mcp` 2.0.0's `Server.__init__` sets `self.middleware = [OpenTelemetryMiddleware()]` by default
(`mcp/server/_otel.py`), wrapping every inbound JSON-RPC message in a protocol-level span. This
repo's own `utils/observability.py` calls `opentelemetry.trace.set_tracer_provider(provider)`
once at startup, gated behind the repo's own optional `[otel]` extra and `cfg.enabled` — the only
thing in the repo that touches the *global* tracer provider. `mcp/shared/_otel.py` captures its
tracer once at import time via the OTel API's `ProxyTracer`, which lazily delegates to whatever
provider is globally registered at span-creation time (not frozen at first call) — this is the
OTel API's standard design for exactly this early-import/late-configure ordering. Net effect:
with `[otel]` installed and enabled, the SDK's protocol-level spans and this repo's
`traced_block()` business-logic spans nest under the same tracer — richer traces, not duplicate
ones. With `[otel]` absent or disabled, the SDK middleware is a total no-op, matching this
repo's zero-overhead-when-disabled philosophy. No code change needed; recorded here because it
was an explicit plan verification item.

**Dependency delta is larger than a single-package pin bump, and `truststore` is transitive, not
direct.** `mcp` 2.0.0's real `requires_dist` (checked against the PyPI JSON API, not assumed):
`httpx2>=2.5.0`, `mcp-types==2.0.0`, `opentelemetry-api>=1.28.0`, `jsonschema>=4.20.0`,
`sse-starlette>=3.0.0`, `uvicorn>=0.31.1`, `pywin32>=311` (win32), `typing-inspection>=0.4.1`,
`pydantic>=2.12.0`, `pyjwt[crypto]>=2.10.1`, `python-multipart>=0.0.9`, `starlette>=0.27`,
`anyio`, `typing-extensions`. `truststore==0.10.4` does get installed by `uv sync --all-extras`,
but `uv tree --invert --package truststore` shows it arrives via `truststore ← httpcore2 ←
httpx2 ← mcp` — a transitive dependency of `httpx2`, not a direct one of `mcp` itself. `httpx2`/
`httpcore2` install alongside (not replacing) the pre-existing `httpx`/`httpcore` used elsewhere
in the repo; no transitive-version conflict materialized.

**StreamableHTTP's bare-GET behavior is healthier than the v1-era assumption, not a regression.**
A bare `GET /mcp` with a wildcard `Accept: */*` (curl's default) is spec-compliant
StreamableHTTP behavior for "client accepts `text/event-stream`": it opens a standalone SSE
stream (`200 OK`, chunked, periodic `: ping` comments) rather than returning `406`. Only an
explicit `Accept: application/json` (excluding `text/event-stream`) triggers the `406 Not
Acceptable` JSON-RPC error body. Both behaviors were exercised directly against the running v2
server; this is more spec-correct than a blanket 406-on-bare-GET expectation and requires no
code change, only accurate expectations in test/verification scripts (bound every such probe
with a timeout — an open SSE stream held by a bare GET does not exit on its own).

## Considered Options

- **Pin `mcp<2` indefinitely** — rejected: the v1 line does not receive the security/CVE fixes
  the version-history entries for prior `mcp` bumps were chasing, and the low-level SDK's
  decorator API is being phased out upstream.
- **Migrate to FastMCP (the high-level v2 API) instead of the low-level `Server`** — rejected:
  the low-level API is what the existing tool/resource/prompt registries
  (`mcp_server/tool_registry.py`) are built around; switching frameworks would be a much larger,
  riskier rewrite than a decorator→kwarg port for no functional gain.
- **Port the six handlers to v2 constructor kwargs, keep the rest of the file unchanged** —
  accepted: `stdio_server`, `server.run(...)`, `create_initialization_options()`, and
  `StreamableHTTPSessionManager(app=, event_store=, json_response=, stateless=)` are all
  unchanged in v2, so the port is scoped to exactly the six handler definitions plus their three
  renamed fields.

## Consequences

- `mcp_server/server.py`'s six handlers now take `(ctx, params)` and return typed v2 result
  objects instead of bare lists/strings; the `Server(...)` construction moved to after all six
  handler `def`s (kwargs need the functions to already exist).
- `mcp_server/tool_registry.py` and its unit test use `input_schema=`/`.input_schema` instead of
  `inputSchema=`/`.inputSchema`.
- `_get_server_version()`'s fallback literal is `"0.23.0"` (was drifted to a stale `"0.21.0"`
  pre-migration).
- Full unit suite (5,401 passed / 2 skipped) is unchanged in count from the pre-migration
  baseline — the rewrite is behavior-preserving at every tested seam.
- `docs/VERSION_HISTORY.md` and `CLAUDE.md`'s Quick Reference version line move to 0.23.0
  alongside this change.
