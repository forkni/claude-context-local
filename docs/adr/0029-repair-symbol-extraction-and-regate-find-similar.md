# Repair `_extract_symbol_from_query` and re-gate the `find_similar` redirect

Status: accepted
Date: 2026-08-04

## Context

ADR-0028 left `find_similar` gated behind `intent.enabled=False` pending a repair of
`_extract_symbol_from_query` (`search/intent_classifier.py`), diagnosed but not yet fixed: four
regexes plus a 3-pass fallback that scans `reversed(query.split())`, accepting any
non-blocklisted `^[a-z][a-z0-9_]+$` token as the redirect's anchor symbol. Measured live against
real golden queries before this round's fix:

| query | returned |
|---|---|
| `find code similar to InheritanceExtractor._extract_from_tree hook` | `'hook'` |
| `find code similar to PythonChunker.__init__` | `'to'` |
| `explore context around _resolve_by_symbol` | `'around'` |
| `what calls PythonChunker.__init__` | `'PythonChunker'` (Pattern 1's `(\w+)` truncates at the dot) |

Two more failure classes: leading-underscore privates (`_resolve_by_symbol`) and UPPER_CONST
(`MAX_RETRIES`) fail all three fallback passes and return `None`.

The same class's `_detect_code_symbols` (used for intent-signal scoring, not extraction) already
solves this correctly: it tokenizes with a dot-preserving regex and ranks matches by four
case-sensitive predicates (camelcase / dotted > snake_or_dunder > upper_const), matching the
project's own boost-precedence table. The fix is to reuse that shape rather than invent a new one.

## Decision

**Promote the tokenizer.** `re.findall(r"[\w.]+", …)` — the only dotted-symbol-preserving tokenizer
in the repo (`normalize_to_tokens` lowercases and camel-splits; `BM25Index._IDENTIFIER_RE` drops
dots) — moved from `_detect_code_symbols`'s body into `search/tokenization.py` as a public
`tokenize_dotted_identifiers(text)` helper, called from both `_detect_code_symbols` and the rewritten
extractor. `TestTokenizationOwnership` scopes the single-tokenization-owner gate to the CamelCase
splitter and two named wrapper functions only, not this pattern, so the promotion doesn't violate it.

**Rewrote `_extract_symbol_from_query`:**

- Patterns 1–4's capture groups widened `(\w+)` → `([\w.]+)`, with `.rstrip(".")` on the match so a
  qualified name (`PythonChunker.__init__`) survives without dot-truncation and an accidental
  trailing sentence period is stripped.
- Pattern 5 (the buggy fallback) replaced with a single-pass selector: tokenize with
  `tokenize_dotted_identifiers`, skip `CODE_TERM_BLOCKLIST` tokens, rank by the same precedence
  `_detect_code_symbols` already uses (camelcase / dotted > snake_or_dunder > upper_const), take the
  highest-ranked token with ties won by the later occurrence in the query. **Returns `None`** when no
  token qualifies — no symbol means no redirect, i.e. normal ranked search, the safe default.
- The four symbol predicates (`is_camelcase`, `is_upper_const`, `is_snake_or_dunder`,
  `is_dotted_symbol`) are **untouched** — changing them to reach all-caps-prefixed PascalCase
  (`HTMLParser`, `GLSLChunker`) or all-lowercase dotted (`self.method`) would break
  `test_tokenization.py`'s pinned semantics. Those two shapes still score zero on all four predicates
  and return `None`, taking the normal path — a known, accepted blind spot: fewer redirects, never a
  wrong one.

**Tests:** nine golden-query regressions (`TestSymbolExtractionGoldenRegressions`, one parametrized
test covering Q70/Q71/Q93–Q99's real query text) pin the exact anchor symbol each must extract, using
verbatim golden-dataset text rather than invented phrasing — a guessed phrasing reproduces a
*different* misfire than the one it's meant to pin. `test_symbol_extraction_no_match` tightened from
`None or isinstance(str)` (passes either way) to strict `is None`. Four new tokenizer-unit tests for
`tokenize_dotted_identifiers`. `TestSymbolDetection`'s boost arithmetic (`_detect_code_symbols`,
including the exact 0.5 cap) verified unchanged through the tokenizer promotion. Commit `3f80f2a`.

### The gate

Pre-registered before capture, on the 9 similarity-category golden queries, required on **both**
datasets:

> MRR must **exceed** the same-substrate normal-path mean, and recall@20 must **not fall below the
> same-substrate F-view (correct-anchor) mean**.

Recall is baselined on the F-view ceiling rather than the normal path deliberately: seed-0
determinism (ADR-0021) makes run noise 0, yet `find_similar` structurally returns a much smaller
candidate pool (~3–11 chunks) than hybrid search's ~29, so even a *perfect* anchor loses recall@20 on
this substrate (F-view 0.7185 vs. normal-path 0.7966). Baselining the recall clause on the normal
path would fail a flawless repair outright; baselining on the ceiling asks the question the round is
actually about — did the extractor find the right anchor, not did `find_similar`'s narrower pool
out-recall a ~29-candidate hybrid search.

### Result — gate PASSED on both datasets

| | control (normal path) | F-view (ceiling) | intent-on arm | verdict |
|---|---|---|---|---|
| mrr (9 F queries) | 0.4594 | 0.8519 | **0.5593** | PASS — arm > control (+0.0999) |
| recall@20 (9 F queries) | 0.7966 | 0.7185 | **0.7418** | PASS — arm ≥ F-view (+0.0233) |

Identical on the 63q and 133q datasets (the 9 F queries score independently of which dataset they run
inside). The MRR gain (+0.0999) lands inside the plan's pre-registered expectation (+0.09 to +0.15);
the arm's absolute MRR (0.5593) lands inside the realistic ceiling band (0.54–0.61) rather than the
raw F-view figure (0.8519) — four of the nine F queries carry a hand-authored
`similar_exclude_same_file=True` annotation the redirect structurally cannot see (Q71's individual
regression from 1.000 to 0.200 is this gap, not an extraction failure: `redirect_kind="find_similar"`
fired and correctly anchored on `InheritanceExtractor._extract_from_tree`, evidenced by the retrieved
set being the class's own sibling methods).

Full capture detail, per-query breakdown, and the substrate-drift accounting against `canon_g1`:
`evaluation/CANON_20260804_INTENT_ON_REPAIRED.md`.

**Disposition:** the gate passed, so `intent.enabled`'s default flips back `False` → `True` in this
same round (`search/config.py`, comment updated to cite this ADR), with `find_similar` now live in
production. `search_config.json` and `search_config.json.example` updated to match (a test enforces
dataclass/example value parity).

## Consequences

- **`canon_h1`'s intent-on arm becomes the published baseline** (63q mrr 0.8418, 133q mrr 0.6750),
  superseding `canon_g1`. The control (intent-off) views are published alongside it as the reference
  point for anyone running with the layer disabled.
- **`find_similar` fires in production again**, now anchored correctly instead of on a
  trailing-prose-word or a dot-truncated symbol.
- **Two known, accepted blind spots ship un-fixed**: all-caps-prefixed PascalCase (`HTMLParser`,
  `GLSLChunker`) and all-lowercase dotted symbols (`self.method`, `chunker.chunk_file`) score zero on
  all four predicates and extract `None`, taking the normal ranked path instead of redirecting. Safe
  by construction — strictly fewer redirects, never a wrong one — and not gated by this round's
  criterion, which only measures the queries that *do* extract a symbol.
- **Live end-to-end MCP re-verification was inconclusive for a process-lifecycle reason, not a code
  reason.** A direct `search_code` call through the already-running MCP server for Q71's exact query
  text returned a redirect anchored on an unrelated symbol — because that server process was started
  before this round's code changes landed and Python does not hot-reload already-imported modules.
  A fresh-process check of the same query (`IntentClassifier().classify(...)` in a new `python.exe`)
  and the benchmark harness's own capture (which runs the real `search_orchestrator.py` redirect path
  in a fresh process per invocation) both confirm the fix is correct in the actual production code
  path — `redirect_kind="find_similar"` fired on Q71 anchored on `InheritanceExtractor._extract_from_tree`
  exactly. The stale-server discrepancy resolves on the next server restart; no code action follows
  from it.

## Verification

`./scripts/test/run_tests.sh tests/unit/ -q` — 5673 passed / 1 skipped (13 net new: 4 tokenizer + 9
golden-query regressions, on top of ADR-0028's −3). `tests/fast_integration/ -q` — 102 passed.
`check_lint.sh --modified-only` and `pyrefly check` both clean. `audit_golden_dataset.py` CLEAN on
both datasets against the fresh 204-file/2323-chunk index. All five `canon_h1` views (63q control,
133q control, F-view, 63q arm, 133q arm) overall PASS. Gate PASSED on both datasets (above).

## Out of scope

- The two accepted blind spots (all-caps PascalCase, all-lowercase dotted) — no static exclusion or
  predicate-widening proposal without new evidence; a prior static-exclusion attempt for a related
  problem was already rejected (`402b1d0`).
- Any change to `QueryIntent` classification, QW5's ego-threshold table, or A1's edge-weight
  profiles — ADR-0026 measured these inert; this round's gate concerned only the `find_similar`
  redirect's anchor accuracy.
- Had the gate failed, the plan for this round was to remove the `find_similar` redirect too and
  record the whole intent layer (classification + QW5 + A1) as a removal candidate on the
  ADR-0015/0016 precedent. Moot — the gate passed.
