# Resolve Rust calls from a rust-analyzer SCIP table (opt-in)

Status: accepted
Date: 2026-11-24

ADR-0091 ("D") resolves Rust plain and path calls through `use` imports, but it
cannot type a receiver. A receiver call `x.m()` still links to every project
method named `m` (ambiguous), and a call to a `std` method such as `.len()` or
`.clone()` links to unrelated project methods with the same name. On hyprzero
these receiver calls were 565k of the 838k Rust `calls` edges.

rust-analyzer knows the receiver types and writes them into a SCIP index. A cold
run on hyprzero takes about 10 minutes (634 s in the probe, 592 s in the gate
run) and 16.5 GB of RAM, so it cannot run inside a reindex. We split it in two:

- **Producer** (`tools/scip_index.py`, launcher menu "Make SCIP Index"). It runs
  `rust-analyzer scip` on demand and writes three files into
  `<storage>/scip/`: `index.scip`, `manifest.json` (a sha256 for every `.rs`
  file; a file that changed during the run is left out) and `refs.sqlite`.
  `search/scip_refs.py` decodes the index with a small protobuf wire reader (no
  new dependency) in about 6 s for hyprzero's 294 MB index. `--digest-only`
  rebuilds `refs.sqlite` from an existing index.
- **Graph-build pass** (`_RustScipPass` in `search/graph_integration.py`, switch
  `call_graph.rust_scip`, default off). It reads the table and decides each Rust
  call, receiver calls included, before D:

  1. The caller file must still have its manifest hash. Otherwise the call goes
     to D (`stale_caller`).
  2. A SCIP reference to a function named like the callee must be on the call's
     line. SCIP has no call role and tree-sitter call sites carry no column, so
     the join is by file, line and name. No reference: `no_ref`. Two different
     symbols: `multi`. Both go to D.
  3. A symbol with no definition in the indexed sources is external: no
     resolved edge, only the bare-name phantom edge (`refused_external`).
  4. rust-analyzer gives same-named items in different targets of one package
     the same symbol string (each `tests/*.rs` file is its own crate). With
     several definitions, only the one in the caller's own file is used.
     Otherwise the call goes to D (`dup_def`).
  5. The definition file must still have its hash (`stale_def`). The target is
     the innermost Rust chunk with that name whose lines hold the definition. No
     such chunk (a trait declaration, a macro-made function) goes to D
     (`unmapped`).

  A resolved call gets one exact edge with `resolution="scip"`,
  `resolver_source="scip"` and `resolver_confidence=0.95`: below LSP's 0.98,
  because the join is by line, not column. Each build logs
  `[RUST_SCIP] resolved= refused_external= no_ref= multi= dup_def=
  stale_caller= stale_def= unmapped= secs=`. With the switch on and no table,
  the build logs one line and runs without the tier. Other languages are
  byte-identical.

## Evidence

The hyprzero Rust graph was built offline twice from the saved metadata, D only
and D plus E (`evaluation/RUST_SCIP_GATE_20261124.md`, local only).

- E was asked about 540,946 Rust calls. It resolved 145,581 and refused 223,766
  as external. The others went to D: 155,807 `no_ref`, 6,313 `multi`, 1,540
  `dup_def` and 7,939 `unmapped`. None were stale (the producer ran just before).
- Changed call sites: 58,267 receiver calls became exact, 55,665 refused
  externals lost false project edges, 21,357 path calls that D left unlinked
  got an edge, and 1,505 path calls got a different target from D's.
- The graph build took 18.6 s against 19.4 s for D alone, because E answers
  many calls before D parses them.
- In the hand-labelled sample, each of the four strata scored 10 of 10 correct
  (strict, Wilson lower bound 0.72). The gate was at least 9 of 10 per stratum
  and at most 20 s extra build time. The first run failed the disagreement
  stratum (8 of 10 rows wrong, all tests that link a same-named helper in
  another test crate). That run found the duplicate-symbol rule (step 4); the
  passing numbers are from the rerun.
- 58% of SCIP function references have no tree-sitter call site: imports,
  functions passed as values, and macro arguments. Calls written inside macro
  arguments stay out of scope.

## Considered options

- **Run rust-analyzer inside the reindex.** Rejected: too slow and too large for
  a normal reindex (see above).
- **Decode `index.scip` in each graph build.** Rejected. The table makes the
  build read only the rows of each caller file, and the producer pays the decode
  once.
- **Use a reference when the file changed but the line still matches.**
  Rejected. A per-file hash is cheap, and a moved line could point an edge at
  the wrong code.
- **Default on.** Rejected for now. The tier needs a 10-minute, 16 GB producer
  run that the user starts, and the table goes stale as files change. Stale
  files fall back to D without error.

## Consequences

- Coverage decays as files change after a producer run. Run "Make SCIP Index"
  again after large edits. A changed file only loses this tier.
- `third_party/` forks that are workspace path dependencies are project
  sources to SCIP, so their methods get edges. A crate from crates.io or git is
  external.
- No retrieval canon re-pin: the switch is off, and the self-index has no Rust
  code.
- Closes the "receiver calls need types" item that ADR-0091 left open.

## Amendments

- 2026-11-24: The Rust chunker now records a call on the line of the called
  name, not on the line where the call expression starts. Before this change,
  a chain written over several lines (`a` on one line, `.b()` on the next)
  recorded `a`'s line. SCIP puts the reference on `b`'s line, so step 2 found
  no reference. In a later hyprzero probe, 77,048 of 152,649 `no_ref` calls
  had the name's reference 1 to 12 lines lower. D is not affected: it uses the line
  only to find the inline module and block-scoped imports that hold the call.
