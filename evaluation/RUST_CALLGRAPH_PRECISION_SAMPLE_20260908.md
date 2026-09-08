# Rust Call-Graph Hand-Labeled Precision Sample (2026-09-08)

Executes Step 2 of the Rust call-graph tier Phase 4 plan: measure real hand-labeled precision on
`openheizenberg`'s Rust call edges and check the default-visible population against the
pre-registered `>= 0.85` strict gate, mirroring
`evaluation/CPP_CALLGRAPH_PRECISION_SAMPLE_20260903.md`'s methodology.

## Methodology

- **Data source**: the persisted call graph for `openheizenberg`
  (`openheizenberg_a2de4cb7_f2llm-v2-0.6b_call_graph.json`; 2,320 nodes / 9,651 edges, 8,692
  `calls`). Filtered to Rust-source `calls` edges (`nodes[source].language == "rust"`), split into
  three strata by `(confidence, is_method)`:
  - **A** = `exact` & `is_method=False` (non-method calls — free functions, associated functions
    like `Type::new()`) — population 667.
  - **B** = `exact` & `is_method=True` (method calls, `self.m()` or otherwise) — population 405.
  - **C** = `ambiguous` & `is_method=True` (downgraded method calls, the sanity stratum) —
    population 1,844, ungated.
  - A + B = 1,072 is the **default-visible** population (`confidence == "exact"`).
- **Sampling**: each stratum sorted by `(source, target, line)` for reproducibility, then a single
  `random.seed(0)` RNG draws **in order A(75), B(75), C(40)** — order matters, the RNG state is
  shared across strata. Total n = 190. Drawer: `tmp/draw_rust_precision_sample.py` (not committed,
  `tmp/` is gitignored); reproducibility verified by re-running it and diffing the output — the
  185-row and 190-row draws are byte-identical across repeated runs.
- **Labeling**: 3-valued (`correct` / `incorrect` / `uncertain`), per the pinned rule in
  `evaluation/RESOLVER_PRECISION_LABELS_20260902.md` — an edge is true only if the caller's body
  **executes** a call or construction of the actual, real callee. A real, executing call that
  resolves to the wrong target is still `incorrect` (the precedent doc's own worked examples —
  "real call, wrong callee id" — establish this). `uncertain` is reserved for calls that are
  statically undecidable even for a human (e.g. dynamic dispatch through `Arc<dyn Trait>` where
  multiple project-wide implementations are all genuinely plausible for that specific call site).
  Every sampled call site and its resolved target's definition were read directly from the live
  `D:\Users\alexk\FORKNI\TWOZERO\openheizenberg` checkout; ambiguous bare-name resolutions were
  disambiguated by grepping every `fn <name>(` definition project-wide and cross-checking argument
  arity, receiver-variable declarations, and (for `serde_json`/std-library collisions) the
  surrounding call pattern.
- Labeled dataset (`tmp/rust_precision_sample_annotated.json`) stays **local-only** per project
  convention — only this writeup is committed.
- **Disclosed peek** (from the plan's pre-flight): before finalizing the design, 398 of 405
  stratum-B call sites were confirmed literally `self.<name>(` (the shape the Wall-2 item-6
  divergence rests on); 7 are not textually matchable that way. One such row landed in the drawn
  75-row sample (index 144, a line-wrapped `self` / `.param_value(...)` split across lines) and
  was labeled by manually reading the source — it is a genuine, correct `self.method()` call. This
  did not change the pre-registered 75/75/40 design.

## Results

Precision reported two ways: **strict** (`correct / total`, uncertain counted as failing — the
gate metric) and **lenient** (`correct / (correct + incorrect)`, uncertain excluded). Wilson 95%
CIs via `wilson_interval()` (`scripts/benchmark/precision_estimate.py:53-64`).

| stratum | n | correct | incorrect | uncertain | strict | strict 95% CI | lenient |
|---|---|---|---|---|---|---|---|
| A (`exact`, non-method) | 75 | 63 | 12 | 0 | **0.840** | [0.741, 0.906] | 0.840 |
| B (`exact`, method) | 75 | 75 | 0 | 0 | **1.000** | [0.951, 1.000] | 1.000 |
| C (`ambiguous`, method — ungated) | 40 | 15 | 25 | 0 | **0.375** | [0.242, 0.530] | 0.375 |

### A + B weighted (default-visible population, the gate)

Population-weighted by stratum size (667/1072 A, 405/1072 B):

- **Weighted strict precision: 0.9004**
- **Weighted lenient precision: 0.9004** (no `uncertain` labels in either stratum)

Pooled-count cross-check (treating the 150 A+B sample rows as one binomial draw, n=150,
correct=138): strict precision **0.920**, Wilson 95% CI **[0.865, 0.954]** — the CI's lower bound
alone clears the `>= 0.85` gate.

**No `uncertain` labels occurred anywhere in the 190-row sample.** Every Rust call site examined
was statically decidable — Rust's `impl Trait for Type` model and lack of overloading make most
calls determinable from local declarations alone; the one class of call that would plausibly earn
`uncertain` (`Arc<dyn NodeType>` dynamic dispatch, `#37` in stratum C, discussed below) instead
drew a *provably wrong* candidate rather than a genuinely-plausible-but-undecidable one, so it is
labeled `incorrect`, not `uncertain`.

## Failure-mode taxonomy

**1. Same-file / global-uniqueness bare-name fallback misfire (stratum A, 12/75 = 16%).** The
dominant, and only systematic, defect in the default-visible population. `_resolve_call_target`
correctly tries a Rust qualified-first lookup (`Params::new` as a literal string) before falling
back to a bare-name lookup — but when the qualifier is an external-crate type, a `type` alias, or
a `#[derive(...)]`-synthesized impl (none of which have a resolvable project `impl` block), the
qualified lookup *legitimately* fails, and the code falls through to matching the **bare method
name** (`new`, `default`, `click`) against same-file or globally-unique project candidates. All 12
observed cases:

- **`Params::new()` -> wrong `::new` (7 occurrences, rows 7/20/31/48/50/65 land on `Graph::new`,
  row 20 lands on `Server::new`)** — `Params` is a `type` alias (`BTreeMap<...>`), never chunked
  under its own name, so it has no `impl` block to resolve against.
- **`Arc::new(...)` -> `Server::new`** (row 17) — a particularly bad case: the caller chunk and
  the resolved target chunk are the *same* chunk (a spurious self-loop), because the call sits
  inside `Server::new` itself and same-file preference picks the enclosing method.
- **`Vec::new()` -> `UndoStack::new`** (row 27), **`Vec2::new(dx, dy)` -> `App::new`** (row 45) —
  external-crate (`std`/`egui`) types.
- **`egui::Context::default()` -> `Harness::default`** (row 23), **`NodeState::default()` ->
  `Graph::default`** (row 67) — external-crate and (very likely) derive-macro-synthesized `Default`
  impls, both with no source chunk.
- **`Sense::click()` -> `Harness::click`** (row 64) — the one case resolved via **global**
  uniqueness rather than same-file coincidence (caller and target are in different files); `click`
  happens to have exactly one project-wide definition, which is not the real (external `egui`)
  callee.

None of these six colliding names (`new`, `default`, `click`) are in `_RUST_COMMON_MEMBERS` (a
30-name blocklist covering `clone`/`unwrap`/iterator/collection methods) — they were never
candidates for that blocklist, since `new`/`default` are exactly the names a real project
constructor *should* resolve to. This is a structurally different failure from the C++ precedent's
"common STL method colliding with an unrelated project class" pattern: here the *qualified* form
was correct and specific, but is silently discarded the moment project lookup fails, rather than
the edge being left unresolved (and falling into `ambiguous`/no-edge) when the qualifier is known
but unresolvable.

**2. Std-library / external-crate method-name collisions inside the ambiguous-fanout-capped set
(stratum C, 16/25 incorrect rows).** The largest share of stratum C's incorrect labels: a bare
method call like `.len()`, `.is_empty()`, `.get()`, `.push()`, `.as_str()`, `.next()`, `.input()`
on a `Vec`/`String`/`HashMap`/`serde_json::Value`/iterator/`egui::Context` receiver has **zero**
correct project candidates, yet `_get_ambiguous_candidates` still returns up to `fanout_cap=3`
project-wide same-named methods as "ambiguous" edges — all of them wrong, because the true callee
is never a project method at all:
`.len()` (rows 3, 4 — byte slice / `Vec<f32>`), `.is_empty()` (rows 8, 14, 22, 33 — `Vec`/`String`),
`.get()` (rows 7, 9, 15, 29, 32 — `serde_json::Value` x3, `HashMap` x2), `.push()` (rows 18, 19,
23, 38 — all `Vec<T>`), `.as_str()` (rows 13, 21, 24 — `String` x2, duplicate draw of one call
site), `.next()` (row 17 — `std::str::RSplit` iterator), `.input()` (row 31 —
`egui::Context::input`, a closure-based API, not `CookContext::input`'s index-based one). This is
the direct Rust analogue of the C++ precedent's "common STL method resolving to an unrelated
project class" — but it lands in the *hidden-by-default* `ambiguous` stratum here, not the
default-visible one, which is exactly what the downgrade is for.

**3. Genuinely multi-candidate ambiguous calls, correctly tagged (stratum C, `cook`/`fps`/`frame`,
4/25 incorrect rows).** `g.cook(1)` (rows 0, 6) resolves to `WithCommon::cook` — but the call
passes one argument and `WithCommon::cook` takes none; the true match by arity is
`Graph::cook(frames: usize)`, one of 29 project-wide `cook` definitions. `g.fps()` (row 28) should
hit the *public* `Graph::fps` (`graph.rs:345`) given the surrounding Snapshot-building context, but
the drawn candidate is a private, unrelated `GraphEnv::fps` (`graph.rs:2399`). `h.frame()` with
zero arguments (row 30) should hit `Harness::frame(&mut self)` (0-arg), but the drawn candidate
`App::frame(&mut self, ctx)` requires an argument — an arity mismatch that alone proves it wrong.
These are cases where the *fanout-capped* set legitimately contains the right answer somewhere
among the 29-30 candidates, but the specific candidate this sample happened to draw was not it —
consistent with `ambiguous_fanout_cap`'s own docstring already flagging `cook`/`spec` as the
project's worst fan-out names.

**4. `Arc<dyn NodeType>` dynamic dispatch drawing a wrong-type (not merely wrong-impl) candidate
(stratum C, row 37, 1/25 incorrect).** `let ty = self.registry.get(type_name)?;` types `ty` as
`Arc<dyn NodeType>` (confirmed via `Registry::get`'s signature at `node.rs:756`); `ty.spec()` is a
trait-object call whose concrete implementation is only known at runtime — genuinely the "Rust
analogue of C++ virtual dispatch" the plan anticipated as `uncertain` territory. But the *specific*
candidate the fanout-capped set drew, `Node::spec` (`graph.rs:85`), is not one of the `NodeType`
trait's per-node-kind implementations at all — `Node` is an unrelated struct with its own plain
`spec()` field accessor. Since the receiver type (`Arc<dyn NodeType>` vs. `Node`) rules it out
completely, this is labeled `incorrect`, not `uncertain` — the drawn candidate is provably wrong
regardless of which concrete `NodeType` impl is actually bound at runtime.

**5. Single-candidate resolution downgraded solely by receiver shape is reliable when it fires
(stratum C's 15 correct rows) — a methodological correction, not a defect.** Investigating why
`self.shared.lock()` (row 1's caller chain) is tagged `ambiguous` at all — `lock` has exactly one
project-wide definition — surfaced that `downgrade_method_confidence`
(`search/graph_integration.py:973-981`) can tag a **single, uniquely-resolved** edge `ambiguous`
without ever invoking the genuinely-multi-candidate branch: for Rust, the downgrade fires whenever
the receiver isn't the literal `self.<name>(` shape (Wall-2 item-6), independent of how many
candidates the bare name actually has. Confirmed for 15 of the 40 sampled rows: `add_node` (rows
2, 39), `graph`/`lock` (rows 1, 5, chained through `self.shared.lock().graph()`), `is_playing`
(row 10), `levels` (row 11), `output` (row 12), `f32`/`i64` (`CookContext` accessors, rows 16, 27),
`sample` (row 20), `step_back` (row 25), `load_into` (row 26), `connect` (row 34), `frames` (row
35), `push_attr` (row 36) — every one globally unique project-wide and semantically consistent
with its call site's receiver type. **This means stratum C's precision (0.375) should not be read
as "the downgrade rule is 37.5% conservative and 62.5% correctly targeted" in a simple sense** — it
conflates two different populations (genuinely-ambiguous multi-candidate calls, and
singly-resolved-but-shape-downgraded calls), and this sample shows the second population resolves
correctly 100% of the time it was checked (15/15), while the *entire* 25-incorrect tally comes
from the genuinely-multi-candidate population. If a future change wanted to promote
shape-downgraded single-candidate Rust method edges back to `exact`, this sample is weak
supporting evidence for doing so safely — but that is new scope, not exercised here.

## What resolves reliably

- **Every stratum-B (`self.method()`) call in the sample: 75/75 correct**, including the one
  line-wrapped non-textual-`self.` outlier. Rust's lack of method overloading plus a unique
  `Type::method` qualified match within the caller's own declared `impl` type is definitionally
  correct — there is no C++-style STL-collision risk because the qualifier is derived from the
  chunking pass's own container-node type, not inferred from receiver text.
- Globally-unique bare-name resolution is reliable whenever the name genuinely has exactly one
  project-wide definition **and** is not itself a std-library/external-crate method name that
  merely happens to coincide (contrast failure modes 1 and 2 above, both of which are "unique or
  same-file, but the true callee isn't a project symbol at all").
- Associated-function calls (`Type::new()`) where `Type` **is** a real, chunked project type with
  its own `impl` block resolve correctly every time in this sample (rows 0, 1, 3, 5, 9, 11, 16,
  26, 29, 30, 32, 37, 38, 40, 42, 44, 46, 47, 52, 54, 59, 61, 69, 70 of stratum A, among others) —
  the qualified-first lookup is doing exactly its intended job there.

## Decision branch evaluation

The plan's pre-registered branch — *"if B lands far below A (the C++ pattern), collapse the
Wall-2 item-6 divergence"* — **does not fire**. The measured result is the opposite direction: B
(1.000) is stronger than A (0.840), not weaker. Unlike the C++ precedent (where unconditional
`is_method=True` downgrade was needed because method-call resolution was catastrophically
unreliable, 16-19% precision), Rust's item-6 divergence — downgrading a method edge only when its
qualified type isn't project-resolvable — is doing real, correctly-targeted work: it is precisely
the *unresolvable-qualifier* method calls (stratum C) that need hiding, and the *resolvable*
ones (stratum B) are reliable enough to stay `exact`. **Verdict: keep the divergence as designed,
no code change.** This is recorded as a measured decision in ADR-0070, not a preference.

## Verdict against the `>= 0.85` gate

**Passes.** Weighted A+B strict precision is **0.9004**, and the pooled-sample Wilson 95% CI lower
bound (**0.865**) independently clears the gate. Stratum A alone (0.840, CI [0.741, 0.906]) sits
just under 0.85 on its point estimate but its CI comfortably overlaps the gate, and it is only
one signed defect class (failure mode 1, 12/75 rows) dragging it down — not diffuse noise. Stratum
B is effectively perfect (1.000, CI [0.951, 1.000]). Stratum C, ungated, measures 0.375 — low, but
correctly hidden from default visibility, and about 60% of its incorrect share (16/25) is the
std-library/external-crate-collision pattern that the downgrade specifically exists to hide, with
the rest (9/25) genuinely multi-candidate fan-out that the existing `hide_ambiguous_edges_default`
machinery (ADR-0069) already suppresses.

**Residual, un-fixed defect for future work**: failure mode 1 (same-file/global-uniqueness
bare-name fallback misfiring when a qualified-first lookup legitimately fails) affects the
*default-visible* population and is the reason stratum A isn't higher. A future fix would need to
distinguish "no qualifier was ever extracted" (safe to fall back to bare-name) from "a qualifier
was extracted but didn't resolve to a project type" (the qualifier's failure should arguably block
the bare-name fallback, or the edge should be tagged `ambiguous` rather than `exact`). This is new
scope, not built in this Phase-4 exercise — recorded in ADR-0070's `## Consequences` /
`## Out of scope`.
