# Remaining-Levers A/B: A4 Reranker Document Representation (2026-08-14)

**Verdict: A4 `signature_head` REJECTED.** `reranker.doc_representation_mode`
stays `"full"` (the shipped default). The knob is settled and added to
`FORBIDDEN_AUTO_TUNE_KEYS` (`search/index_probe.py`) with citation. No default
flips from this campaign.

Campaign scope (approved plan, 2026-08-14): four remaining levers after Track A
closed. B1 and B4 are display-layer ships with no benchmark surface; A3 died at
its pre-registered probe gate before reaching an arm; A4 is the only
benchmarked arm.

| Lever | Commit | Outcome |
|---|---|---|
| B1 `hide_ambiguous` (find_connections) | `63c1840` | SHIPPED (opt-in, default False) |
| B4 `include_top_callers` (search_code) | `a20c805` | SHIPPED (opt-in, default False) |
| A4 `doc_representation_mode` mechanism | `9b2b917` | SHIPPED disabled; arm REJECTED (this doc) |
| A3 graph-channel final-pool reserve | `6cc7caf` | NOT BUILT — probe gate failed (`evaluation/GRAPH_RESERVE_PROBE_20260814.md`) |

## Substrate

Post-`6cc7caf` corpus (all four implementation commits landed), one incremental
reindex before the campaign (22 modified files, 203 chunks re-embedded), 2,403
vectors. Deterministic harness conventions: PYTHONHASHSEED=0 auto-re-exec,
`CLAUDE_AUTO_REINDEX=0`, `--set intent.enabled=true` on every run, one fresh
process per arm (the knob is construction-baked), full non-tail'd logs with
`--set overrides:` echo lines verified for both A4 arms.

Artifacts (gitignored): `benchmark_results/remaining_levers/{base_63q_r1,
base_63q_r2,base_133q_r1,a4_sighead_63q,a4_sighead_133q}.{json,log}` +
`analyze_ab.py` (paired-CI analysis script).

## New deterministic canons (this substrate)

- **63q canonical: MRR 0.8722, pool_hit_rate 0.9206** — r1 vs r2 bit-identical,
  0 per-query movers. Identical to the pre-campaign Track-A canon, which
  doubles as proof the four implementation commits were quality-neutral at
  their defaults.
- **133q expanded: MRR 0.6843, recall@10 0.7898, recall@20 0.8309,
  pool_hit_rate 0.9248** (`base_133q_r1`). Supersedes the Track-A 0.6773 canon
  (substrate drift from the implementation commits + reindex). Note the
  hard-miss set drifted with it: H034 (0.5) and H066 (1.0) are no longer
  mrr=0 on this substrate; Q101/Q106/Q117/Q122/H008/H050 remain misses.

## A4 — `signature_head` arm (`--set reranker.doc_representation_mode=signature_head`)

Representation: `path | parent` context line + docstring (≤300 chars) + first
12 source lines, replacing the full `bm25_text` body in listwise reranker
documents (JinaRerankerV3/GenerativeReranker; plain cross-encoder out of scope).

### 133q upside gate — FAILED (CI-negative, not merely null)

| metric | base | arm | Δ mean | paired 95% CI | gate |
|---|---|---|---|---|---|
| recall@10 | 0.7898 | 0.7108 | **−0.0789** | [−0.1291, −0.0288] | **EXCLUDES 0, loss** |
| recall@20 | 0.8309 | 0.7573 | **−0.0736** | [−0.1256, −0.0215] | **EXCLUDES 0, loss** |
| recall@5 | 0.6668 | 0.6151 | −0.0516 | [−0.0943, −0.0089] | excludes 0, loss |
| recall@50 | 0.8347 | 0.7573 | −0.0773 | [−0.1287, −0.0259] | excludes 0, loss |
| ndcg@10 | 0.6961 | 0.6481 | −0.0480 | [−0.0844, −0.0116] | excludes 0, loss |
| mrr | 0.6843 | 0.6401 | −0.0441 | [−0.0909, +0.0026] | guard-rail: loss at edge of noise |
| pool_hit_rate | 0.9248 | 0.8571 | −0.0677 | — | 11 lost vs 2 gained |

47 MRR movers. pool_hit gained: H027, H054 (both 0→1.0 MRR). pool_hit lost:
Q101, H003, H012, H023, H032, H033, H034, H045, H049, H063, H066 — including
H066 (1.0→0.0) and H034 (0.5→0.0), the two golds A1's graph evidence had shown
reachable, and ranking-target H063 (0.083→0.0).

### 63q guard-rail — ALSO VIOLATED

| metric | base | arm | Δ mean | paired 95% CI |
|---|---|---|---|---|
| mrr | 0.8722 | 0.8384 | −0.0339 | [−0.0873, +0.0196] |
| recall@10 | 0.8089 | 0.7798 | −0.0291 | [−0.0589, +0.0007] |
| recall@5 | 0.7002 | 0.6666 | **−0.0336** | [−0.0661, −0.0011] excludes 0 |
| pool_hit_rate | 0.9206 | 0.9206 | 0.0000 | — |

Q12 1.0→0.0, Q19 1.0→0.2 among 10 movers. The canonical set — which has zero
hard misses and nothing to gain — is actively harmed at recall@5.

### Mechanism

The representation change reaches *pool membership*, not just final ordering:
the hop-1 rerank cut (top-20) and the merged-pool rerank window are both
listwise passes over the same documents, so compressing every document reshapes
which candidates survive the funnel. The compressed form rescues a few golds
whose head/docstring happens to carry the query vocabulary (H027, H054, Q117
0→0.5, Q114 0.33→1.0) but drops body-evidence golds wholesale — a net 11-vs-2
pool trade and a CI-negative recall aggregate on both datasets.

### Latency (informational)

Shorter documents make the listwise passes ~19% faster: 63q 3944→3204 ms/query
(−740), 133q 4185→3391 ms/query (−794). This is the knob's only win. If a
latency campaign ever wants it, the recall debit above is the priced-in cost —
same disposition shape as PPR (documented opt-in, never default).

## B1 / B4 (no benchmark surface)

Display-layer, opt-in, default-off, byte-identity covered by unit tests at each
layer (registry → handler → impl). Live MCP end-to-end sanity (find_connections
± `hide_ambiguous`; search_code + `include_top_callers`) deferred until the
code-search MCP server restarts on the new code.

## Methodology notes

- 63q r1/r2 identity (0 movers) re-confirms PYTHONHASHSEED=0 determinism on the
  new substrate — per-query deltas in the A4 arms are causal, not flap.
- The 133q baseline hard-miss set is substrate-dependent (H034/H066 exited the
  miss set this round without any intervention). Re-derive the miss cohort from
  the current baseline before targeting it; the 2026-08-02 list of 9 is stale.
- Gate was pre-registered before any arm ran: recall@10/20 paired 95% CI
  excluding zero on 133q for upside, MRR guard-rail both sets, aggregates only.
  The arm failed in the opposite direction — CI excludes zero on the *loss*
  side for every recall metric on 133q.
