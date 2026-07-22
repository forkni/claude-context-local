#!/usr/bin/env node
// Dependency-free stdio <-> StreamableHTTP bridge for the local MCP server.
// Reads newline-delimited JSON-RPC on stdin, POSTs each to the HTTP server,
// writes JSON responses to stdout. No OAuth, no callback port, instant start.
const http = require("http");
const { URL } = require("url");

const TARGET = process.env.CODE_SEARCH_URL || "http://localhost:8765/mcp";
const target = new URL(TARGET);
let sessionId = null;

function log() { console.error.apply(console, ["[code-search-bridge]"].concat([].slice.call(arguments))); }

function post(message) {
  return new Promise(function (resolve) {
    const payload = Buffer.from(JSON.stringify(message), "utf8");
    const headers = {
      "Content-Type": "application/json",
      "Accept": "application/json, text/event-stream",
      "Content-Length": payload.length
    };
    if (sessionId) headers["Mcp-Session-Id"] = sessionId;
    const req = http.request(
      { hostname: target.hostname, port: target.port || 80, path: target.pathname + target.search, method: "POST", headers },
      function (res) {
        const sid = res.headers["mcp-session-id"];
        if (sid) sessionId = sid;
        let body = "";
        res.setEncoding("utf8");
        res.on("data", function (c) { body += c; });
        res.on("end", function () { resolve({ status: res.statusCode, ctype: res.headers["content-type"] || "", body: body }); });
      }
    );
    req.on("error", function (e) { log("upstream error:", e.message); resolve({ status: 0, ctype: "", body: "" }); });
    req.write(payload);
    req.end();
  });
}

function extractJson(ctype, body) {
  if (!body) return null;
  if (ctype.indexOf("text/event-stream") >= 0) {
    const out = [];
    body.split(/\r?\n/).forEach(function (line) {
      if (line.indexOf("data:") === 0) {
        const d = line.slice(5).trim();
        if (d) { try { out.push(JSON.parse(d)); } catch (e) {} }
      }
    });
    return out;
  }
  try { return [JSON.parse(body)]; } catch (e) { return null; }
}

async function handle(line) {
  let msg;
  try { msg = JSON.parse(line); } catch (e) { return; }
  const res = await post(msg);
  const msgs = extractJson(res.ctype, res.body);
  if (msgs) msgs.forEach(function (m) { process.stdout.write(JSON.stringify(m) + "\n"); });
}

let chain = Promise.resolve();
let buf = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", function (chunk) {
  buf += chunk;
  let idx;
  while ((idx = buf.indexOf("\n")) >= 0) {
    const line = buf.slice(0, idx).trim();
    buf = buf.slice(idx + 1);
    if (line) chain = chain.then(function () { return handle(line); });
  }
});
// Drain any in-flight requests before exiting so late responses are not lost.
process.stdin.on("end", function () { chain.then(function () { setTimeout(function () { process.exit(0); }, 100); }); });
log("ready ->", TARGET);