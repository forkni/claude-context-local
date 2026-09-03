# C/C++ Call-Graph Hand-Labeled Precision Sample (2026-09-03)

Executes plan task #13 (`docs/plans/IMPLEMENTATION_PLAN_CALLGRAPH_RECALL_20260901.md`) and the
follow-up recommended by `evaluation/CPP_CALLGRAPH_PROBE_20260903.md`: measure real hand-labeled
precision on resolved (non-phantom) C-family call edges, and check it against the plan's
`>= 0.85` gate.

## Methodology

- **Data source**: `<slug>_call_graph.json` for voro-engine (the same post cast-operator-fix
  graph measured in `CPP_CALLGRAPH_PROBE_20260903.md`; 18,241 nodes, 67,298 edges). Filtered to
  `type=='calls'` edges whose source node's `language` is `c`/`cpp` and whose `confidence` is
  `exact` or `ambiguous` (phantom edges, which carry no `confidence` key, are excluded by
  construction). This filter reproduces the probe doc's counts exactly: 6,452 exact + 4,398
  ambiguous = 10,850 resolved edges.
- **Sampling**: `random.seed(0)`, then `random.sample(exact_edges, 110)` and
  `random.sample(ambiguous_edges, 70)`, concatenated (exact-stratum first, ambiguous second) for
  180 total sampled edges — uniform random within each stratum, not first-N, to avoid
  file-traversal-order bias.
- **Labeling**: for every sampled edge, the actual call-site source line (with surrounding
  context) and the actual resolved target's definition were read directly from the voro-engine
  checkout and judged `correct` / `incorrect` / `uncertain`. A label is `correct` only when the
  call-site expression's real receiver/callee genuinely matches the resolved definition (verified
  via surrounding-code type evidence — declarations, STL container idioms, namespace
  qualification, same-file/same-class locality); `incorrect` when the evidence clearly shows a
  different type/symbol was intended; `uncertain` when the call site is statically undecidable
  even by a human reader (e.g. dispatch through a function pointer or virtual interface with
  multiple plausible project-wide implementations) or evidence is genuinely ambiguous.
- Labeled dataset (`tmp/precision_labels.json`) stays **local-only** per project convention —
  only this writeup is committed.

## Results

Precision reported two ways: **strict** (`correct / total`, uncertain counted as failing) and
**lenient** (`correct / (correct + incorrect)`, uncertain excluded). The gate check below uses
strict, the more conservative reading.

| stratum | n | correct | incorrect | uncertain | precision (strict) | precision (lenient) |
|---|---|---|---|---|---|---|
| exact | 110 | 90 | 19 | 1 | **0.818** | 0.826 |
| ambiguous | 70 | 15 | 35 | 20 | **0.214** | 0.300 |
| **overall** | **180** | **105** | **54** | **21** | **0.583** | **0.660** |

### Breakdown by `is_method`

| group | n | correct | incorrect | uncertain | precision (strict) | precision (lenient) |
|---|---|---|---|---|---|---|
| `is_method=False` (free functions) | 112 | 94 | 8 | 10 | 0.839 | **0.922** |
| `is_method=True` (member calls) | 68 | 11 | 46 | 11 | **0.162** | 0.193 |

This is the central finding: free-function call resolution is reliable (92% lenient precision,
driven almost entirely by same-file locality, in-class unqualified static/member calls, and
namespace-qualified calls matching a canonically-named shared header). Member-call (`.method()`
/ `->method()`) resolution is the opposite — only 16-19% precision — and it is what drags the
overall number well under the gate. `is_method=True` is 38% of the sample (68/180) but supplies
46 of the 54 confirmed-incorrect labels (85%) and 11 of 21 uncertain labels.

## Failure-mode taxonomy (with concrete examples)

**1. Common STL/container method names resolving to unrelated project classes.** By far the
dominant failure. Tree-sitter has no type information (documented, expected limitation —
ADR-0060 Consequences), so `_C_FAMILY_COMMON_MEMBERS`'s "unless the project defines it" escape
hatch cannot check whether the *correct* receiver type defines the method, only whether *some*
project class does — and it resolves to whichever one exists, right class or not.

- `#4` (exact): `KernelFxPlugin.cpp:2353` — `if (!error.empty())` where `error` is a
  `std::string` (from the `!error.empty()` guard usage) resolves to
  `include/cito/show_core.h:75 ShowId::empty()` — an unrelated fixed-buffer ID class. The same
  `.empty()`-on-`ShowId` mistarget recurs at `#62`, `#77`, `#93`, `#104` — five separate call
  sites (a `std::string`, an audio-sample `std::vector<float>`, a Win32 device-name string, an
  `fs::path`, and another `fs::path`) all misresolving to the same single `ShowId::empty()`.
- `#20` / `#30` / `#61`: three different `.count()` calls — a `std::chrono::duration::count()`
  (`engine.cpp:9759`), a `std::set<std::string>::count()` (`engine.cpp:19358`), and another
  `std::chrono::duration::count()` (`tools/cuda_first_bracket_matrix.cu:680`) — all resolve to
  `include/voro/phys/phys_space.h:86 SpeakerLayout::count()`, an unrelated speaker-array size
  accessor.
- `#26` / `#63` / `#97`: three `.size()` calls on plain `std::vector`s all resolve to
  `src/engine/engine.cpp:3012 TensorDispatchPool::size()`.
- `#54` / `#105`: `std::find(surfaces.begin(), surfaces.end(), ...)` and
  `open_.begin()->first` (a `std::map` iterator) both resolve to
  `include/voro/acoustic/scene_ingest.h:216 SceneIngest::begin(float version)` — a single-arg
  scene-versioning method, not an iterator.
- `#55` / `#106`: a `std::unique_ptr::get()` and an `nlohmann::json::get<float>()` template call
  both resolve to `tools/cuda_first_bracket_matrix.cu:509 ShareableVmmWords::get()`, a CUDA
  shared-memory wrapper.

**2. `#include` directives matched as call targets.** `#119`, `#131`, `#166`, `#179` — every
`json::array({...})` call site in the sample (an nlohmann::json factory call) resolves to an
`#include <array>` preprocessor-directive node (e.g. `include/cito/music_algorithms.h:11`), not
a function at all. An include node has no call semantics; this is unambiguously wrong and a
distinct bug class from (1).

**3. Cross-language mis-resolution.** Three instances: `#28`
(`tools/cuda_first_bracket_matrix.cu:661`, `gate->cv.wait(...)` on a `std::condition_variable`)
resolves to a **Python** `PortWaiter.wait` method in `tools/diag_tensor_input_race.py`; `#140`
(`plugins/audio/spectral/spectral.cpp`, `SimpleFFT::transform(...)`) resolves to a Python
`split_block:transform` chunk in `plugins/effects_candidates/sources/bitmosh/main.py`; `#175`
(`tools/acoustic_scene_gate.cpp:745`, `write_wav(path, buf, 6, SR)`, 4 args) resolves to a
**Python** `def write_wav(path: Path, samples: np.ndarray) -> None` in
`tools/build_audio_sample_review.py` (2 params) — both a cross-language and an arity mismatch at
once.

**4. Arity mismatch (verifiable without any type inference).** `#137`:
`plugins/play_drum_fix/play_drum_fix.cpp` calls `osc_sin(v.ph[i], hz, fsr)` (3 arguments);
resolves to `plugins/note_voice_oscillator/note_voice_oscillator.cpp:67 osc_sin(float ph)`
(1 parameter). Just counting arguments is enough to know this is wrong.

**5. Genuinely undecidable dispatch (the honest share of `ambiguous`).** A recurring, distinct
pattern in the `uncertain` bucket, not attributable to a resolver bug: calls through a
struct-of-function-pointers descriptor (`decl->reset_state(...)`, `plugin->allocate_state(...)`,
e.g. `#115`, `#123`, `#128`, `#145`, `#160`, `#171`, `#174`) or through a polymorphic backend
interface pointer (`g.backend->enumerate(...)`, `s->backend->closeAll()`, e.g. `#127`, `#134`,
`#154`, `#165`) where several project-wide implementations are equally plausible and no static,
type-free analysis can pick the one actually bound at runtime. The resolver's own `ambiguous`
confidence tag is honestly earned here. A related, quieter version of the same problem: `#130`
and `#158` both call a same-named local helper `cf(...)` from `play_drum_v2.cpp`, and land on
*two different* target files (`drum_synth_studio.cpp:cf` vs. `drum_synth.cpp:cf`) — direct,
reproducible evidence that this codebase's pervasive per-plugin helper duplication (`cf`, `ci`,
`clamp_int`, `fc_make`, `hash_u32`, `white`, `midi_to_hz` all recur across multiple files in this
sample alone) creates real multi-candidate ambiguity even for ordinary free functions, not just
member calls.

## What resolves reliably

Same-file free-function calls, in-class unqualified calls to a sibling method/static method of
the same class, and namespace-qualified calls matching a canonically single-defined shared
header (`cito_arrangement::bpm_at_beat`, `cito_music::clamp_float`, `cito_platform::get_env`,
`cito_manifest::is_manifest_filename`, etc.) were correct in every instance checked in this
sample — these are the resolver's strong suit and the reason the free-function `is_method=False`
lenient precision reaches 0.922.

## Verdict against the plan's `>= 0.85` gate

**Fails, decisively.** Overall measured precision is 0.583 (strict) / 0.660 (lenient) — both far
below 0.85. Even the best-case reading (exact-tier only, lenient) reaches only 0.826, still under
gate. The failure is concentrated and mechanistically explained, not random noise: it is
`is_method=True` member-call resolution specifically (16-19% precision) colliding with common
STL/container method names on non-project types, exactly the risk ADR-0060's Consequences section
flagged as a known, accepted limitation of a type-blind tier-1 resolver — now quantified rather
than theoretical. `is_method=False` free-function resolution clears the gate comfortably on its
own (0.839-0.922).

**Implication for the plan**: the `>= 0.85` gate as a single blended number is not achievable by
this tier without type information (tiers 2/3, explicitly deferred per ADR-0035's unmet reopening
condition). If this gate is to stay a hard pass/fail bar, it should likely be split by
`is_method` — free-function precision already clears 0.85, member-call precision does not and
would need either a narrower project-defined-method allowlist, dropping the "unless the project
defines it" escape hatch for the common-STL-member blocklist, or downgrading `is_method=True`
edges to a lower confidence tier (e.g. `speculative`, excluded from default traversal) rather than
`exact`/`ambiguous`. That is a scoping decision for whoever picks up the next step, not made here.
