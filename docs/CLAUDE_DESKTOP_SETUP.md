# Claude Desktop Setup Guide

Connect the **code-search** MCP server to the **Claude Desktop** app so Desktop chats can use
all 18 semantic search tools — pointing at the **same running HTTP server** that Claude Code uses.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Configuration](#configuration)
4. [Activate & Verify](#activate--verify)
5. [Troubleshooting](#troubleshooting)
6. [Related Documentation](#related-documentation)

---

## Overview

The MCP server runs in **StreamableHTTP** transport at `http://localhost:8765/mcp` (see the
[StreamableHTTP transport section](INSTALLATION_GUIDE.md#5-mcp-stdio-transport-issues) in the
installation guide). Because the server runs stateless and accepts multiple concurrent
connections, **Claude Desktop and Claude Code can connect to the same server process at the same
time** — you do not need to start a second copy.

### Why Desktop needs a bridge

| Client | How it connects to the HTTP server |
|--------|------------------------------------|
| **Claude Code** | Native `"type": "http"` entry in `~/.claude.json` → connects to `http://localhost:8765/mcp` directly. |
| **Claude Desktop** | Its config (`claude_desktop_config.json`) natively speaks **stdio** only, and its "Add custom connector" UI is brokered through Anthropic's cloud (requires a **public HTTPS** URL). A plain `http://localhost` URL is rejected. |

To bridge Desktop's stdio to the local HTTP server, we use **[`mcp-remote`](https://www.npmjs.com/package/mcp-remote)**
— a small npx-run adapter that translates stdio ⇄ Streamable HTTP. Desktop launches it as a child
process; it forwards every request to the already-running server on port 8765.

> **Shared-state caveat**: Because both clients talk to one server process, they share server
> state — the **active project** and loaded indices/model. If you switch the active project from
> Desktop (`switch_project`), Claude Code sees the change too, and vice versa.

---

## Prerequisites

1. **The HTTP server is running** on `http://localhost:8765/mcp`. Start it with either:
   - `scripts\batch\start_mcp_http.bat`, or
   - `start_mcp_server.cmd` → **Quick Start Server**.

   Confirm the log shows `Uvicorn running on http://localhost:8765` and `APPLICATION READY`.

2. **Node.js installed** — provides `npx`, which runs `mcp-remote`. Verify:

   ```powershell
   node --version
   ```

   If missing, install the LTS build from [nodejs.org](https://nodejs.org/).

---

## Configuration

Edit Claude Desktop's config file:

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

Open it via Claude Desktop → **Settings → Developer → Edit Config** (this creates the file if it
doesn't exist), or edit the file directly.

Add the `code-search` entry, merging into any existing `mcpServers` block:

```json
{
  "mcpServers": {
    "code-search": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://localhost:8765/mcp",
        "--allow-http",
        "--transport",
        "http-only"
      ]
    }
  }
}
```

**Flag notes:**

- `-y` — auto-installs `mcp-remote` on first run (no manual `npm install` needed).
- `--allow-http` — **required**. `mcp-remote` refuses plain (non-HTTPS) URLs without it.
- `--transport http-only` — the server is StreamableHTTP with JSON responses (no SSE); this pins
  the bridge to HTTP and skips SSE negotiation. It can be omitted (the bridge auto-negotiates), but
  pinning it is more reliable.

> **JSON tip**: If you already have other servers under `mcpServers`, add `code-search` as a
> sibling key — don't create a second `mcpServers` block. A single missing comma or bracket
> silently disables **all** servers.

---

## Activate & Verify

1. **Fully quit and restart Claude Desktop** — the config file is read only at startup.
   (On Windows, quit from the tray/menu, not just the window close button.)

2. In a chat, click the **"+" / connectors menu** in the input box and confirm **`code-search`**
   appears with its tools listed.

3. Ask a natural-language question that triggers a search, e.g.:

   > "Search the codebase for the embedding model loader."

   Confirm Claude runs a `code-search` tool call and returns results. (Tools are exposed as
   `mcp__code-search__*` and invoked implicitly — there are no slash commands.)

---

## Troubleshooting

**`code-search` not listed after restart**

- Confirm the HTTP server is up: open `http://localhost:8765` in a browser, or check
  `logs\mcp_server.log` for `APPLICATION READY`.
- Run the bridge command manually in a terminal to see the real error:

  ```powershell
  npx -y mcp-remote http://localhost:8765/mcp --allow-http
  ```

- Validate the JSON (a stray comma disables every server). Paste it into any JSON linter.

**Read Desktop's MCP logs**

- **Windows**: `%APPDATA%\Claude\logs\mcp*.log` (per-server file: `mcp-server-code-search.log`)
- **macOS**: `~/Library/Logs/Claude`
- `mcp.log` covers general connection failures; the per-server file holds the bridge's stderr.

**`npx` / Node not found** — install Node.js LTS from [nodejs.org](https://nodejs.org/), then
restart Desktop.

**The "Add custom connector" UI rejects `http://localhost:8765/mcp`** — this is expected. That flow
requires a public HTTPS endpoint; use the `mcp-remote` bridge above instead (it is the supported
path for a local, no-auth HTTP server).

**Tools appear but calls fail** — verify the server still runs and the active project is indexed
(switching projects affects both clients — see the shared-state caveat above).

---

## Related Documentation

- **[INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)** — full install; Claude **Code** MCP
  configuration and the StreamableHTTP transport rationale.
- **[MCP_TOOLS_REFERENCE.md](MCP_TOOLS_REFERENCE.md)** — all 18 tools, parameters, and examples.
