#!/usr/bin/env python
"""Probe context cost per resolved query, read-only.

Background: ``docs/plans/preprints202510.0924.v1.pdf`` (Jain 2025, *An
Exploratory Study of Code Retrieval Techniques in Coding Agents*) compares 7
coding agents on one retrieval task and finds an 8,500-117,000 token spread
(14x) in what task completion *costs* -- all 7 agents complete the task, so
context cost per resolved query is the differentiator, not success/failure.
That axis is one this project has never measured: ``evaluation/metrics.py``
has zero size/token math, and ``run_sscg_benchmark.py`` passes
``max_context_tokens: 0``, which disables the only token estimator on the
live path (``mcp_server/tools/search_orchestrator.py``'s Block H,
``_apply_source_order_and_budget``). This probe makes that axis gateable.

Two structural facts motivate it (both verified live via MCP before this
probe was written -- see
``docs/plans/CODE_RETRIEVAL_AGENT_DISPOSITION_20260818.md`` P1/P2):

- ``search_code`` returns coordinates only (``file``, ``lines``, ``kind``,
  ``score``, ``chunk_id``, optionally ``name``/``reranker_score``/
  ``complexity_score``/``source`` -- see ``result_view._format_search_results``).
  No ``content``/``bm25_text``/etc field is ever emitted. The caller must
  ``Read`` whole files to act on a hit -- ``downstream_read_cost`` below
  measures exactly that externalized cost.
- ``ego_graph_enabled=False`` in the ``run()`` arguments dict does **not**
  disable ego-graph expansion. That per-request ``SearchPlan`` flag only
  ever flips ``True`` (intent-suggestion) and defaults ``False`` already, so
  a caller-supplied ``False`` is a no-op either way. The actual gate is the
  **config-level** ``EgoGraphConfig.enabled`` field
  (``config.ego_graph.enabled``, default ``True``) -- confusingly sharing
  the identical ``flat_alias="ego_graph_enabled"`` string with the inert
  per-request flag. This probe's ``ego_contract`` metric mutates the config
  field directly (snapshot/False/restore per query, cheap -- not among
  ``SearchConfig._CONSTRUCTION_BAKED_FIELDS``, no searcher rebuild needed).

Payload field-set is NOT stable across queries -- a reranked hybrid query
carries ``reranker_score``, an auto-routed BM25 query does not, only
``blended_score``. Every metric here is computed per-query from whatever the
payload actually contains, never from an assumed fixed schema.

``search_mode`` is deliberately **omitted** from every ``run()`` call here
(unlike ``run_sscg_benchmark.py``, which hardcodes ``search_mode="hybrid"``
and pins ``intent.enabled=False`` for benchmark-arm comparability) so this
probe measures the real deployed-default payload an agent actually gets:
auto/intent-classified routing, ``IntentConfig.enabled=True`` by default.
A redirect (``similar_chunks`` / ``path_found`` instead of ``results``) is
therefore an expected outcome, not an error -- recorded via ``redirect_kind``.

``gold_sufficiency`` is computed **strictly** from the raw formatted payload
dicts (``response["results"]`` as literally returned) -- never from
``metadata_store``-rehydrated metadata, which would contaminate the very
finding this metric proves (search_code is coordinates-only, so
content-level sufficiency should structurally measure 0.0 today; see
Verification step 3 in the disposition doc).

Reused, not re-implemented, from the shared probe harness and production
modules (per-probe reimplementation of any of this is exactly the drift this
harness exists to prevent -- ``docs/adr/0040-probe-harness-seam.md``):

- ``evaluation/probe_harness.py``: ``ensure_pinned_hash_seed`` (ADR-0021,
  under ``__main__`` only), ``probe_parser``, ``resolve_dataset_path``,
  ``load_golden_queries`` (category D excluded by its own default -- this
  probe loads category D separately, see below), ``open_probe``/
  ``ProbeSession`` (searcher + live config lifecycle), ``write_probe_json``.
- ``mcp_server.tools.search_orchestrator.SearchOrchestrator``: the single
  production entry point that actually builds the agent-visible payload --
  ``evaluation/probe_harness.py``'s ``ProbeSession`` operates on
  ``HybridSearcher`` internals and does not build it.
- ``mcp_server.tools.search_handlers.handle_find_connections``: the
  production ``find_connections`` handler, for the ``connections_fanout``
  metric (L4) -- higher-fidelity than replaying ``RelationshipAnalyzer``
  directly (``run_caller_recall.py``'s approach), since it exercises the
  real decorator stack (``@error_handler``, ``@require_indexed_project``)
  and ``hide_ambiguous`` default.
- ``mcp_server.output_formatter.format_response``: the exact
  verbose/compact/ultra formatting production applies outside ``run()``
  (``mcp_server/server.py``), for ``format_savings``.
- ``evaluation.metrics.normalize_chunk_id``: gold-chunk-id comparison.

Golden corpora used:

- ``--dataset`` (default ``evaluation/golden_dataset_expanded.json``) minus
  category D, via ``load_golden_queries`` -- the ``tokens_returned``/
  ``k_drift``/``gold_sufficiency``/``downstream_read_cost``/
  ``signature_view_delta``/``ego_contract`` corpus.
- The **14 category-D entries** in that same dataset, read directly (they
  carry no ``symbol_name``/``target_chunk_id`` field, so
  ``load_golden_queries`` is the wrong tool for them) -- the secondary,
  "dead weight in every campaign" ``connections_fanout`` corpus, resolved to
  a ``symbol_name`` via a best-effort heuristic (dotted-path regex, then a
  stopword-filtered fallback; manually verified against all 14 query strings
  before use here).
- ``evaluation/caller_golden.json`` + ``evaluation/callee_golden.json`` (7 +
  7 entries, category E, direct ``target_chunk_id`` fields) -- the primary
  ``connections_fanout`` corpus.

Constraints: read-only (no config writes survive past their own query's
counterfactual, no reindex, no ``--set`` mutation beyond harness-standard
apply-and-restore). ``PYTHONHASHSEED=0`` self-pinned via
``ensure_pinned_hash_seed`` (ADR-0021). ``CLAUDE_AUTO_REINDEX=0`` is an
**operator-set env var** (``search/config.py``'s ``enable_auto_reindex``
reads it directly) -- export it yourself before running, this script never
sets it programmatically, matching every other probe's convention. No
production code is touched; the ``ego_contract`` config mutation is
snapshotted and restored around each query's counterfactual call.

Usage (module form required -- ``scripts`` is not in the editable-install
package map, ADR-0040):
    .venv/Scripts/python.exe -m scripts.benchmark.probe_context_cost \\
        [--dataset evaluation/golden_dataset_expanded.json] [--project-path .] \\
        [--k 10] [--query-ids Q121 ...] [--json out.json] \\
        [--connections-max-depth 3]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import statistics
import sys
from pathlib import Path
from typing import Any

from evaluation import probe_harness
from evaluation.metrics import normalize_chunk_id


try:
    import tiktoken

    _ENCODING = tiktoken.get_encoding("cl100k_base")
except Exception:  # noqa: BLE001 - resilience: tiktoken is an optional cross-check, never fatal
    _ENCODING = None


OUTPUT_FORMATS: tuple[str, ...] = ("verbose", "compact", "ultra")

# Fields that would make a result "content-sufficient" rather than merely
# "located" -- none of these are ever emitted by result_view._format_search_results
# today; this metric is expected to measure a structural 0.0 (see module docstring).
CONTENT_FIELD_CANDIDATES: tuple[str, ...] = (
    "content",
    "content_preview",
    "text",
    "source_code",
    "snippet",
    "bm25_text",
    "raw_content",
)

# Matches output_formatter._to_toon_format's dynamic header key, e.g.
# "results[11]{chunk_id,kind,score}" -- the ultra-format array-of-dicts
# encoding, needed since "results" as a literal key no longer exists there.
_TOON_HEADER_RE = re.compile(r"^(\w+)\[(\d+)\]\{")

_QUERY_STOPWORDS = frozenset(
    {
        "what",
        "which",
        "who",
        "whom",
        "calls",
        "call",
        "called",
        "does",
        "do",
        "the",
        "a",
        "an",
        "function",
        "method",
        "class",
        "of",
        "in",
        "to",
        "is",
        "are",
        "for",
        "and",
        "how",
        "this",
        "that",
        "code",
    }
)

DEFAULT_CONNECTIONS_MAX_DEPTH = 3


# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------


def count_tokens_tiktoken(text: str) -> int | None:
    """Real ``cl100k_base`` token count, or None if tiktoken is unavailable."""
    if _ENCODING is None or not text:
        return 0 if text == "" else None if _ENCODING is None else None
    return len(_ENCODING.encode(text))


def count_tokens_prod_heuristic(results: list[dict[str, Any]]) -> int:
    """Production's exact per-result heuristic, verbatim from
    ``mcp_server/tools/search_orchestrator.py``'s Block H
    (``_apply_source_order_and_budget``): ``len(json.dumps(r)) // 4``,
    summed **per result** -- not ``len(json.dumps(whole_list)) // 4``, which
    would count the list's own bracket/comma overhead differently than
    production's truncation loop does.
    """
    return sum(len(json.dumps(r)) // 4 for r in results)


# ---------------------------------------------------------------------------
# Small parsing / extraction helpers
# ---------------------------------------------------------------------------


def _negative_evidence_key(redirect_kind: str | None) -> str:
    """Name of the key that carries this response's results list, given its
    redirect (see module docstring's "A redirect ... is therefore an
    expected outcome"). ``find_similar`` redirects (``handle_find_similar_code``,
    returned unmodified by ``search_orchestrator.py``'s ``PlanRedirect``
    path) use ``similar_chunks``, never ``results`` -- checking only
    "results" for these would misreport every one of them as P11 regardless
    of whether the formatter is actually dropping anything. No corpus
    ``find_path`` redirects exist in the current golden dataset (verified:
    zero ``redirect_kind == "find_path"`` entries), so that case is left
    unhandled rather than guessed at.
    """
    return "similar_chunks" if redirect_kind == "find_similar" else "results"


def _result_count(formatted: dict[str, Any], redirect_kind: str | None = None) -> int:
    """Number of results in a formatted payload, across all three
    ``output_format`` shapes. ``ultra`` renames the carrier key (see
    ``_negative_evidence_key``) to a dynamic ``<key>[N]{...}`` header key; an
    empty results list vanishes entirely under compact/ultra
    (``_to_compact_format``/``_to_toon_format`` both skip
    ``value in ([], {}, None, "")`` unless the key is in
    ``output_formatter.NEVER_DROP_EMPTY_KEYS``) -- see
    ``_results_key_present`` for detecting that specific case (P11's
    negative-evidence defect).
    """
    key = _negative_evidence_key(redirect_kind)
    if key in formatted:
        value = formatted[key]
        return len(value) if isinstance(value, list) else 0
    for k in formatted:
        match = _TOON_HEADER_RE.match(k)
        if match and match.group(1) == key:
            return int(match.group(2))
    return 0


def _results_key_present(
    formatted: dict[str, Any], redirect_kind: str | None = None
) -> bool:
    """Whether this response's negative-evidence carrier key (``results``,
    or ``similar_chunks`` under a ``find_similar`` redirect -- see
    ``_negative_evidence_key``) is present at all, in any of the three
    formats' encodings -- False on an empty list under compact/ultra
    demonstrates P11 (negative evidence silently dropped) directly.
    """
    key = _negative_evidence_key(redirect_kind)
    if key in formatted:
        return True
    return any(
        _TOON_HEADER_RE.match(k) and _TOON_HEADER_RE.match(k).group(1) == key
        for k in formatted
    )


def _parse_lines(lines_str: str) -> tuple[int, int]:
    """Parse a "start-end" line-range string (result_view._format_search_results'
    ``lines`` field) into ``(start, end)``, or ``(0, 0)`` on any parse failure.
    """
    try:
        start_s, end_s = lines_str.split("-", 1)
        return int(start_s), int(end_s)
    except (ValueError, AttributeError):
        return 0, 0


def _extract_signature_estimate(text: str, max_lines: int = 15) -> str:
    """Reimplementation of ``chunking/languages/python.py``'s
    ``_extract_signature`` line-scan against a plain ``bm25_text`` string --
    the original takes a tree-sitter node + source bytes, not a string, so it
    cannot be imported directly. Extends it with ``"class "`` recognition
    (search_code returns non-function chunk kinds too) and a ``max_lines``
    safety cap for pathological one-arg-per-line signatures. Measurement-only
    for the L3 counterfactual; no production refactor is implied.
    """
    lines = text.split("\n")
    sig_lines: list[str] = []
    seen_start = False
    for line in lines[:max_lines]:
        sig_lines.append(line)
        stripped = line.strip()
        if stripped.startswith(("def ", "async def ", "class ")):
            seen_start = True
        if seen_start and stripped.endswith(":"):
            break
    return "\n".join(sig_lines)


_DOTTED_SYMBOL_RE = re.compile(
    r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b"
)


def _extract_symbol_heuristic(query: str) -> str | None:
    """Best-effort ``symbol_name`` extraction from a category-D
    natural-language query (e.g. "What calls IndexManager.build_index?")
    for use as ``find_connections``' ``symbol_name`` param. Category-D
    entries carry no ``symbol_name``/``target_chunk_id`` field -- this
    heuristic was manually verified against all 14 category-D query strings
    before use. Not a general-purpose NLP extractor; secondary/dead-weight
    corpus only (see module docstring) -- the primary ``connections_fanout``
    corpus is ``caller_golden.json``/``callee_golden.json``'s
    ``target_chunk_id``, which needs no extraction.
    """
    dotted = _DOTTED_SYMBOL_RE.findall(query)
    if dotted:
        return dotted[0]
    candidates = [
        tok.strip("?.,:;'\"()")
        for tok in query.split()
        if tok.strip("?.,:;'\"()").lower() not in _QUERY_STOPWORDS
        and len(tok.strip("?.,:;'\"()")) > 2
    ]
    for tok in candidates:
        if "_" in tok or (
            len(tok) > 1 and tok[0].isalpha() and any(c.isupper() for c in tok[1:])
        ):
            return tok
    return candidates[-1] if candidates else None


# ---------------------------------------------------------------------------
# Golden corpus loading (category D + relationship goldens -- deliberately
# NOT named load_queries/load_golden_queries: tests/unit/evaluation/
# test_probe_hygiene.py ratchets that exact name pattern, and these are not
# general-purpose golden-query loaders, they read a fixed extra shape).
# ---------------------------------------------------------------------------


def _load_category_d_entries(dataset_path: Path) -> list[dict[str, Any]]:
    """Raw category-D entries (natural-language find_connections queries).

    ``evaluation.probe_harness.load_golden_queries`` excludes category D by
    default -- these have no ``symbol_name``/``target_chunk_id`` and aren't
    graded against ``search_code`` results, so reusing that loader for them
    would be a misuse, not a reuse.
    """
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    return [q for q in data["queries"] if q.get("category") == "D"]


def _load_relationship_golden(path: Path) -> list[dict[str, Any]]:
    """``caller_golden.json``/``callee_golden.json`` entries with a
    ``target_chunk_id`` -- the primary ``connections_fanout`` corpus.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    return [q for q in data["queries"] if q.get("target_chunk_id")]


# ---------------------------------------------------------------------------
# Per-query metrics
# ---------------------------------------------------------------------------


def _downstream_read_cost(
    results: list[dict[str, Any]], project_root: Path
) -> dict[str, Any]:
    """Tokens the caller must spend to act on a coordinates-only payload,
    bounded two ways: (a) whole-file read of every distinct file among
    ``results`` (the paper's observed agent behaviour, P6/P8), (b) targeted
    ``start_line``-``end_line`` span read. Read-only from the payload's own
    ``file``/``lines`` strings + the filesystem; missing/renamed files are
    skipped and counted, never fatal.
    """
    whole_files_seen: set[str] = set()
    whole_file_tokens = 0
    targeted_span_tokens = 0
    missing_files = 0
    for r in results:
        rel = r.get("file")
        if not rel:
            continue
        path = project_root / rel
        if not path.is_file():
            missing_files += 1
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            missing_files += 1
            continue
        if rel not in whole_files_seen:
            whole_files_seen.add(rel)
            tok = count_tokens_tiktoken(text)
            whole_file_tokens += tok if tok is not None else len(text) // 4
        start, end = _parse_lines(r.get("lines", ""))
        if start and end and end >= start:
            file_lines = text.split("\n")
            span = "\n".join(file_lines[max(start - 1, 0) : end])
            tok = count_tokens_tiktoken(span)
            targeted_span_tokens += tok if tok is not None else len(span) // 4
    return {
        "distinct_files": len(whole_files_seen),
        "whole_file_tokens": whole_file_tokens,
        "targeted_span_tokens": targeted_span_tokens,
        "missing_files": missing_files,
    }


def _signature_view_tokens(
    results: list[dict[str, Any]], metadata_store: Any
) -> int | None:
    """Sum of ``_extract_signature_estimate`` token counts over ``results``,
    read from ``metadata_store``'s persisted ``bm25_text`` -- the L3
    counterfactual. Returns None (not 0) when no metadata_store is available,
    so callers can distinguish "measured zero" from "couldn't measure".
    """
    if metadata_store is None:
        return None
    total = 0
    for r in results:
        chunk_id = r.get("chunk_id")
        if not chunk_id:
            continue
        entry = metadata_store.get(chunk_id)
        text = (entry or {}).get("metadata", {}).get("bm25_text") if entry else None
        if not text:
            continue
        sig = _extract_signature_estimate(text)
        tok = count_tokens_tiktoken(sig)
        total += tok if tok is not None else len(sig) // 4
    return total


async def probe_query(
    orchestrator: Any,
    session: probe_harness.ProbeSession,
    item: probe_harness.GoldenQuery,
    k: int,
    project_root: Path,
    metadata_store: Any,
    format_response: Any,
    include_signatures: bool = False,
) -> dict[str, Any]:
    """One query's full context-cost measurement: baseline payload economics
    (tokens/bytes/result_count per output_format), the L2 ego-graph-disable
    counterfactual, gold_sufficiency (located vs content-present vs
    signature-present), and the L3 signature-view counterfactual against
    downstream_read_cost.

    ``include_signatures`` wires the shipped ``search_code`` display flag
    into the request itself (production path), while ``signature_present``
    below and ``_signature_view_tokens`` above independently recompute the
    same extractor over ``metadata_store``'s ``bm25_text`` -- keeping both
    lets ``signature_present_rate`` observe the real wire field rather than
    only the offline estimate.

    ``search_mode`` is deliberately omitted (real default-agent routing) --
    see module docstring for why this diverges from
    ``run_sscg_benchmark.py``'s hardcoded ``"hybrid"``.
    """
    arguments = {
        "query": item.query,
        "k": k,
        "include_context": True,
        "max_context_tokens": 0,
        "include_signatures": include_signatures,
    }
    response = await orchestrator.run(dict(arguments))

    redirect_kind: str | None = None
    raw_results = response.get("results")
    if raw_results is None:
        if response.get("similar_chunks") is not None:
            redirect_kind = "find_similar"
            raw_results = response.get("similar_chunks") or []
        elif "path_found" in response:
            redirect_kind = "find_path"
            raw_results = []
        else:
            raw_results = []

    # ---- k_drift + source histogram of the excess (settles L2's
    # interleaved-vs-appended question at the raw, pre-format level) ----
    k_drift = len(raw_results) - k
    excess = raw_results[k:] if len(raw_results) > k else []
    excess_source_histogram: dict[str, int] = {}
    for r in excess:
        src = r.get("source") or "unspecified"
        excess_source_histogram[src] = excess_source_histogram.get(src, 0) + 1
    full_source_histogram: dict[str, int] = {}
    for r in raw_results:
        src = r.get("source") or "unspecified"
        full_source_histogram[src] = full_source_histogram.get(src, 0) + 1

    # ---- tokens_returned@k: production heuristic + real tiktoken count ----
    prod_tokens = count_tokens_prod_heuristic(raw_results)
    real_tokens = count_tokens_tiktoken(json.dumps(raw_results))

    # ---- per-output_format payload_bytes / result_count (format_savings) ----
    # Byte counts must match mcp_server/server.py's real wire serialization
    # exactly, not just any json.dumps: verbose is pretty-printed
    # (indent=2, bigger), compact/ultra use compact separators (",", ":")
    # with no indent (smaller). Using the same json.dumps call for all three
    # (as an earlier version of this probe did) undercounts verbose and
    # overcounts compact/ultra, biasing format_savings low -- caught by
    # cross-checking against a standalone handle_search_code call in
    # Verification step 4.
    format_stats: dict[str, dict[str, Any]] = {}
    for fmt in OUTPUT_FORMATS:
        formatted = format_response(response, fmt)
        if fmt == "verbose":
            blob = json.dumps(formatted, indent=2, default=str)
        else:
            blob = json.dumps(formatted, separators=(",", ":"), default=str)
        format_stats[fmt] = {
            "payload_bytes": len(blob.encode("utf-8")),
            "result_count": _result_count(formatted, redirect_kind),
            "results_key_present": _results_key_present(formatted, redirect_kind),
        }
    verbose_bytes = format_stats["verbose"]["payload_bytes"] or 1
    format_savings = {
        fmt: round(1 - format_stats[fmt]["payload_bytes"] / verbose_bytes, 4)
        for fmt in OUTPUT_FORMATS
    }

    # ---- L2: ego-graph-disable counterfactual. Mutates config.ego_graph.enabled
    # directly -- NOT the inert per-request ego_graph_enabled flag, which
    # only ever flips True and defaults False already (see module docstring).
    # Cheap: not in SearchConfig._CONSTRUCTION_BAKED_FIELDS, no searcher
    # rebuild. Snapshotted and restored around this one call. ----
    cfg = session.config
    prior_ego_enabled = cfg.ego_graph.enabled
    cfg.ego_graph.enabled = False
    try:
        response_ego_off = await orchestrator.run(dict(arguments))
    finally:
        cfg.ego_graph.enabled = prior_ego_enabled
    ego_off_results = response_ego_off.get("results") or []
    ego_on_non_ego_ids = [
        r.get("chunk_id") for r in raw_results if r.get("source") != "ego_graph"
    ]
    ego_off_ids = [r.get("chunk_id") for r in ego_off_results]
    ego_contract = {
        "ego_on_result_count": len(raw_results),
        "ego_off_result_count": len(ego_off_results),
        "ego_off_within_k": len(ego_off_results) <= k,
        "ego_actually_disabled": (
            len(ego_off_results) < len(raw_results)
            or full_source_histogram.get("ego_graph", 0) == 0
        ),
        "truncation_semantics": (
            "appended_only"
            if ego_off_ids == ego_on_non_ego_ids[: len(ego_off_ids)]
            else "interleaved_or_reranked"
        ),
    }

    # ---- gold_sufficiency: located (chunk_id present) vs sufficient
    # (a content field present) -- strictly from raw_results, never
    # metadata_store (see module docstring). ----
    gold_ids = {cid for cid, grade in item.grades.items() if grade > 0}
    top_k = raw_results[:k]
    located = (
        any(normalize_chunk_id(r.get("chunk_id", "")) in gold_ids for r in top_k)
        if gold_ids
        else None
    )
    content_present = (
        any(
            normalize_chunk_id(r.get("chunk_id", "")) in gold_ids
            and any(r.get(f) for f in CONTENT_FIELD_CANDIDATES)
            for r in top_k
        )
        if gold_ids
        else None
    )
    # ---- signature_present: L3's opt-in `signature` field, kept separate
    # from CONTENT_FIELD_CANDIDATES/content_present -- a signature is not
    # body content, and content_present's structural 0.0 must stay intact
    # as a baseline finding regardless of include_signatures. ----
    signature_present = (
        any(
            normalize_chunk_id(r.get("chunk_id", "")) in gold_ids and r.get("signature")
            for r in top_k
        )
        if gold_ids
        else None
    )

    downstream = _downstream_read_cost(top_k, project_root)
    signature_tokens = _signature_view_tokens(top_k, metadata_store)

    return {
        "id": item.id,
        "category": item.category,
        "query": item.query,
        "redirect_kind": redirect_kind,
        "k": k,
        "k_drift": k_drift,
        "excess_source_histogram": excess_source_histogram,
        "full_source_histogram": full_source_histogram,
        "tokens_returned": {
            "production_heuristic": prod_tokens,
            "tiktoken_cl100k": real_tokens,
        },
        "format_stats": format_stats,
        "format_savings": format_savings,
        "ego_contract": ego_contract,
        "gold": {
            "has_gold": bool(gold_ids),
            "located": located,
            "content_present": content_present,
            "signature_present": signature_present,
        },
        "downstream_read_cost": downstream,
        "signature_view_tokens": signature_tokens,
        "signature_view_delta": {
            variant: (
                None
                if downstream[variant] is None or signature_tokens is None
                else downstream[variant] - signature_tokens
            )
            for variant in ("whole_file_tokens", "targeted_span_tokens")
        },
    }


# ---------------------------------------------------------------------------
# connections_fanout (L4)
# ---------------------------------------------------------------------------


def _summarize_connections_response(
    query_id: str | None,
    chunk_id: str | None,
    symbol_name: str | None,
    response: dict[str, Any],
) -> dict[str, Any]:
    blob = json.dumps(response, default=str)
    return {
        "id": query_id,
        "chunk_id": chunk_id,
        "symbol_name": symbol_name,
        "error": response.get("error"),
        "total_impacted": response.get("total_impacted"),
        "file_count": response.get("file_count"),
        "direct_callers": len(response.get("direct_callers") or []),
        "direct_callees": len(response.get("direct_callees") or []),
        "indirect_callers": len(response.get("indirect_callers") or []),
        "payload_bytes": len(blob.encode("utf-8")),
        "tokens_tiktoken": count_tokens_tiktoken(blob),
    }


async def probe_connections_fanout(
    handle_find_connections: Any,
    caller_entries: list[dict[str, Any]],
    callee_entries: list[dict[str, Any]],
    d_entries: list[dict[str, Any]],
    max_depth: int,
) -> dict[str, Any]:
    """``find_connections`` payload size per symbol -- L4's measurement.

    Primary corpus: ``caller_golden.json``/``callee_golden.json``'s
    ``target_chunk_id`` (14 entries, category E). Secondary/dead-weight
    corpus: the 14 category-D natural-language queries
    ``run_sscg_benchmark.py`` auto-excludes from scoring, via
    ``_extract_symbol_heuristic``. No production limit/``max_results``
    exists on this call path (``search/relationship_analyzer.py``,
    ``graph/graph_queries.py``) -- this measures what that means in payload
    terms, it does not impose one.
    """
    primary: list[dict[str, Any]] = []
    for entry in caller_entries + callee_entries:
        target = entry["target_chunk_id"]
        response = await handle_find_connections(
            {"chunk_id": target, "max_depth": max_depth}
        )
        primary.append(
            _summarize_connections_response(entry.get("id"), target, None, response)
        )

    secondary: list[dict[str, Any]] = []
    for entry in d_entries:
        query = entry.get("query", "")
        symbol = _extract_symbol_heuristic(query)
        if not symbol:
            secondary.append(
                {
                    "id": entry.get("id"),
                    "query": query,
                    "skipped": "symbol_extraction_failed",
                }
            )
            continue
        response = await handle_find_connections(
            {"symbol_name": symbol, "max_depth": max_depth}
        )
        secondary.append(
            _summarize_connections_response(entry.get("id"), None, symbol, response)
        )

    return {"primary": primary, "secondary": secondary}


# ---------------------------------------------------------------------------
# Aggregation / reporting
# ---------------------------------------------------------------------------


def _mean(values: list[float]) -> float | None:
    return round(statistics.fmean(values), 3) if values else None


def _median(values: list[float]) -> float | None:
    return round(statistics.median(values), 3) if values else None


def _p90(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = min(int(len(ordered) * 0.9), len(ordered) - 1)
    return ordered[idx]


def summarize(
    reports: list[dict[str, Any]], connections_report: dict[str, Any]
) -> dict[str, Any]:
    """Gate-relevant rollup across the whole run."""
    k_drifts = [r["k_drift"] for r in reports]
    prod_tokens = [r["tokens_returned"]["production_heuristic"] for r in reports]
    real_tokens = [
        r["tokens_returned"]["tiktoken_cl100k"]
        for r in reports
        if r["tokens_returned"]["tiktoken_cl100k"] is not None
    ]
    prod_mean = statistics.fmean(prod_tokens) if prod_tokens else None
    ratio = (
        round(statistics.fmean(real_tokens) / prod_mean, 3)
        if real_tokens and prod_mean
        else None
    )

    payload_bytes_by_fmt = {
        fmt: [r["format_stats"][fmt]["payload_bytes"] for r in reports]
        for fmt in OUTPUT_FORMATS
    }
    format_savings_means = {
        fmt: _mean([r["format_savings"][fmt] for r in reports])
        for fmt in OUTPUT_FORMATS
    }
    # P11 check: how often does an empty results list survive under each format?
    results_vanished = {
        fmt: sum(
            1
            for r in reports
            if r["format_stats"][fmt]["result_count"] == 0
            and not r["format_stats"][fmt]["results_key_present"]
        )
        for fmt in OUTPUT_FORMATS
    }

    gold_rows = [r["gold"] for r in reports if r["gold"]["has_gold"]]
    located_rate = _mean([1.0 if g["located"] else 0.0 for g in gold_rows])
    content_present_rate = _mean(
        [1.0 if g["content_present"] else 0.0 for g in gold_rows]
    )
    signature_present_rate = _mean(
        [1.0 if g["signature_present"] else 0.0 for g in gold_rows]
    )

    ego_off_within_k_rate = _mean(
        [1.0 if r["ego_contract"]["ego_off_within_k"] else 0.0 for r in reports]
    )
    ego_actually_disabled_rate = _mean(
        [1.0 if r["ego_contract"]["ego_actually_disabled"] else 0.0 for r in reports]
    )
    truncation_semantics_histogram: dict[str, int] = {}
    for r in reports:
        sem = r["ego_contract"]["truncation_semantics"]
        truncation_semantics_histogram[sem] = (
            truncation_semantics_histogram.get(sem, 0) + 1
        )

    signature_deltas_whole = [
        r["signature_view_delta"]["whole_file_tokens"]
        for r in reports
        if r["signature_view_delta"]["whole_file_tokens"] is not None
    ]
    signature_deltas_span = [
        r["signature_view_delta"]["targeted_span_tokens"]
        for r in reports
        if r["signature_view_delta"]["targeted_span_tokens"] is not None
    ]

    redirect_histogram: dict[str, int] = {}
    for r in reports:
        rk = r["redirect_kind"] or "none"
        redirect_histogram[rk] = redirect_histogram.get(rk, 0) + 1

    primary_bytes = [c["payload_bytes"] for c in connections_report["primary"]]
    secondary_bytes = [
        c["payload_bytes"]
        for c in connections_report["secondary"]
        if "payload_bytes" in c
    ]
    primary_impacted = [
        c["total_impacted"]
        for c in connections_report["primary"]
        if c["total_impacted"] is not None
    ]
    secondary_skipped = sum(
        1 for c in connections_report["secondary"] if "skipped" in c
    )

    return {
        "n_queries": len(reports),
        "k_drift": {
            "mean": _mean(k_drifts),
            "median": _median(k_drifts),
            "max": max(k_drifts) if k_drifts else None,
            "nonzero_count": sum(1 for d in k_drifts if d != 0),
        },
        "tokens_returned": {
            "production_heuristic_mean": round(prod_mean, 2) if prod_mean else None,
            "tiktoken_mean": _mean(real_tokens) if real_tokens else None,
            "tiktoken_to_production_ratio": ratio,
        },
        "payload_bytes": {
            fmt: {
                "mean": _mean(payload_bytes_by_fmt[fmt]),
                "median": _median(payload_bytes_by_fmt[fmt]),
                "p90": _p90(payload_bytes_by_fmt[fmt]),
            }
            for fmt in OUTPUT_FORMATS
        },
        "format_savings_mean": format_savings_means,
        "results_vanished_count": results_vanished,
        "gold_sufficiency": {
            "n_with_gold": len(gold_rows),
            "located_rate": located_rate,
            "content_present_rate": content_present_rate,
            "signature_present_rate": signature_present_rate,
        },
        "ego_contract": {
            "ego_off_within_k_rate": ego_off_within_k_rate,
            "ego_actually_disabled_rate": ego_actually_disabled_rate,
            "truncation_semantics_histogram": truncation_semantics_histogram,
        },
        "signature_view_delta_mean": {
            "whole_file_tokens": _mean(signature_deltas_whole),
            "targeted_span_tokens": _mean(signature_deltas_span),
        },
        "redirect_histogram": redirect_histogram,
        "connections_fanout": {
            "primary_n": len(connections_report["primary"]),
            "secondary_n": len(connections_report["secondary"]),
            "secondary_skipped": secondary_skipped,
            "primary_mean_payload_bytes": _mean(primary_bytes),
            "secondary_mean_payload_bytes": _mean(secondary_bytes),
            "primary_mean_total_impacted": _mean(primary_impacted),
        },
    }


def print_summary(summary: dict[str, Any]) -> None:
    print(f"\n=== Context-cost probe over {summary['n_queries']} queries ===")

    kd = summary["k_drift"]
    print("\n--- k_drift (requested k vs len(results)) ---")
    print(
        f"mean={kd['mean']} median={kd['median']} max={kd['max']} nonzero={kd['nonzero_count']}"
    )

    tr = summary["tokens_returned"]
    print("\n--- tokens_returned@k ---")
    print(
        f"production_heuristic_mean={tr['production_heuristic_mean']} "
        f"tiktoken_mean={tr['tiktoken_mean']} "
        f"tiktoken/production_ratio={tr['tiktoken_to_production_ratio']}"
    )

    print("\n--- payload_bytes / format_savings by output_format ---")
    print(
        f"{'format':>8} {'mean_bytes':>11} {'median':>8} {'p90':>8} {'savings':>9} {'vanished':>9}"
    )
    for fmt in OUTPUT_FORMATS:
        pb = summary["payload_bytes"][fmt]
        print(
            f"{fmt:>8} {pb['mean'] or 0:>11.0f} {pb['median'] or 0:>8.0f} "
            f"{pb['p90'] or 0:>8.0f} {summary['format_savings_mean'][fmt]:>9} "
            f"{summary['results_vanished_count'][fmt]:>9}"
        )

    gs = summary["gold_sufficiency"]
    print("\n--- gold_sufficiency (strictly from the raw payload) ---")
    print(
        f"n_with_gold={gs['n_with_gold']} located_rate={gs['located_rate']} "
        f"content_present_rate={gs['content_present_rate']} "
        "(expected structural 0.0 -- search_code returns coordinates only) "
        f"signature_present_rate={gs['signature_present_rate']}"
    )

    ec = summary["ego_contract"]
    print("\n--- ego_contract (L2: config.ego_graph.enabled=False counterfactual) ---")
    print(
        f"ego_off_within_k_rate={ec['ego_off_within_k_rate']} "
        f"ego_actually_disabled_rate={ec['ego_actually_disabled_rate']} "
        f"truncation_semantics={ec['truncation_semantics_histogram']}"
    )

    sv = summary["signature_view_delta_mean"]
    print("\n--- signature_view_delta (L3 counterfactual, mean tokens avoided) ---")
    print(
        f"whole_file_tokens={sv['whole_file_tokens']} targeted_span_tokens={sv['targeted_span_tokens']}"
    )

    print(f"\n--- redirect_histogram --- {summary['redirect_histogram']}")

    cf = summary["connections_fanout"]
    print("\n--- connections_fanout (L4) ---")
    print(
        f"primary_n={cf['primary_n']} secondary_n={cf['secondary_n']} "
        f"secondary_skipped={cf['secondary_skipped']} "
        f"primary_mean_payload_bytes={cf['primary_mean_payload_bytes']} "
        f"secondary_mean_payload_bytes={cf['secondary_mean_payload_bytes']} "
        f"primary_mean_total_impacted={cf['primary_mean_total_impacted']}"
    )


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


async def _async_main(args: argparse.Namespace) -> dict[str, Any]:
    from mcp_server.output_formatter import format_response
    from mcp_server.tools.search_handlers import handle_find_connections
    from mcp_server.tools.search_orchestrator import SearchOrchestrator

    dataset_path = probe_harness.resolve_dataset_path(args.dataset)
    items = probe_harness.load_golden_queries(dataset_path, args.query_ids)
    d_entries = _load_category_d_entries(dataset_path)
    caller_entries = _load_relationship_golden(
        probe_harness.REPO_ROOT / "evaluation" / "caller_golden.json"
    )
    callee_entries = _load_relationship_golden(
        probe_harness.REPO_ROOT / "evaluation" / "callee_golden.json"
    )

    orchestrator = SearchOrchestrator()

    with probe_harness.open_probe(args) as session:
        project_root = Path(args.project_path).resolve()
        metadata_store = getattr(
            getattr(session.searcher, "dense_index", None), "metadata_store", None
        )

        reports = []
        for i, item in enumerate(items, 1):
            print(f"[{i:3d}/{len(items)}] {item.id}", flush=True)
            reports.append(
                await probe_query(
                    orchestrator,
                    session,
                    item,
                    args.k,
                    project_root,
                    metadata_store,
                    format_response,
                    include_signatures=args.include_signatures,
                )
            )

        print(
            f"\n[connections_fanout] {len(caller_entries) + len(callee_entries)} primary, "
            f"{len(d_entries)} secondary",
            flush=True,
        )
        connections_report = await probe_connections_fanout(
            handle_find_connections,
            caller_entries,
            callee_entries,
            d_entries,
            max_depth=args.connections_max_depth,
        )

        summary = summarize(reports, connections_report)
        print_summary(summary)

        payload = {
            "substrate": {
                "dataset": str(dataset_path),
                "project_path": str(project_root),
                "k": args.k,
                "connections_max_depth": args.connections_max_depth,
                "include_signatures": args.include_signatures,
                "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
                "tiktoken_available": _ENCODING is not None,
            },
            "reports": reports,
            "connections_fanout": connections_report,
            "summary": summary,
        }
        if args.json_out:
            probe_harness.write_probe_json(args.json_out, payload)
        return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        parents=[probe_harness.probe_parser(__doc__.splitlines()[0])],
    )
    parser.add_argument(
        "--connections-max-depth", type=int, default=DEFAULT_CONNECTIONS_MAX_DEPTH
    )
    parser.add_argument(
        "--include-signatures",
        action="store_true",
        help="Pass include_signatures=True on every search_code call (L3's "
        "opt-in display flag), so gold_sufficiency.signature_present_rate "
        "measures the real wire field instead of only the offline estimate.",
    )
    args = parser.parse_args()

    try:
        asyncio.run(_async_main(args))
    except (OSError, KeyError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    probe_harness.ensure_pinned_hash_seed()
    sys.exit(main())
