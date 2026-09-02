#!/usr/bin/env python3
"""Build and score execution-witnessed call-graph ground truth (WS-B).

Two subcommands, both argparse-only and deterministic (every output list is
sorted, so no PYTHONHASHSEED pin is needed). Run as a module from the repo root
(no hand-rolled ``sys.path`` bootstrap, per ``test_probe_hygiene``):

    # 1. Intersect raw pytest-plugin runs and map endpoints to chunk ids.
    .venv/Scripts/python.exe -m scripts.benchmark.traced_callgraph build \\
        --runs evaluation/traced_runs/r1.json evaluation/traced_runs/r2.json \\
               evaluation/traced_runs/r3.json \\
        --project-name claude-context-local \\
        --out evaluation/traced_callgraph.json

    # 2. Score each resolver tier of the persisted call graph against it.
    .venv/Scripts/python.exe -m scripts.benchmark.traced_callgraph score \\
        --traced evaluation/traced_callgraph.json \\
        --project-name claude-context-local \\
        --out evaluation/resolver_tier_scores.json

Raw runs come from::

    PYTHONHASHSEED=0 ./scripts/test/run_tests.sh tests/unit -q -p no:randomly \\
        --timeout=0 -p evaluation.tracer.pytest_callgraph --callgraph-trace \\
        --callgraph-output evaluation/traced_runs/r1.json

Exit codes: 0 success, 1 index lookup failure, 2 integrity failure
(``schema_ok`` or ``density_ok`` false).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from evaluation.index_locator import (
    AmbiguousIndexError,
    IndexNotFoundError,
    IndexPaths,
    find_index,
    open_metadata_store,
)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")
    os.replace(tmp, path)
    print(f"wrote {path}")


def _locate(args: argparse.Namespace) -> IndexPaths:
    return find_index(
        args.project_name, storage=args.storage, model_slug=args.model_slug
    )


def _index_block(paths: IndexPaths, chunks: int) -> dict[str, Any]:
    return {
        "project_dir": str(paths.project_dir),
        "metadata_db": str(paths.metadata_db),
        "call_graph": str(paths.call_graph),
        "chunks": chunks,
    }


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


def cmd_build(args: argparse.Namespace) -> int:
    from evaluation.tracer.build import (
        build_line_map,
        build_traced_callgraph,
        intersect_runs,
        load_run,
    )

    paths = _locate(args)
    runs = [load_run(p) for p in args.runs]
    inter = intersect_runs(runs)
    store = open_metadata_store(paths)
    try:
        chunks = len(store)
        line_map = build_line_map(store)
    finally:
        store.close()
    payload = build_traced_callgraph(
        inter,
        line_map,
        run_files=[str(Path(p).as_posix()) for p in args.runs],
        index=_index_block(paths, chunks),
    )
    _write_json(Path(args.out), payload)
    integ = payload["integrity"]
    print(
        "integrity: "
        + " ".join(f"{k}={v}" for k, v in integ.items())
        + f" | executed_chunks={len(payload['executed_chunks'])}"
        + f" edges={len(payload['edges'])} test_edges={len(payload['test_edges'])}"
    )
    for d in payload["dropped"]:
        print(f"dropped {d['reason']}: {d['count']}")
        for ex in d["examples"][:3]:
            print(f"    {ex}")
    return 0 if integ["schema_ok"] and integ["density_ok"] else 2


# ---------------------------------------------------------------------------
# score
# ---------------------------------------------------------------------------


def _load_goldens(golden_dir: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for direction, name in (
        ("callers", "caller_golden.json"),
        ("callees", "callee_golden.json"),
    ):
        path = golden_dir / name
        if path.is_file():
            out[direction] = json.loads(path.read_text(encoding="utf-8"))
    return out


def cmd_score(args: argparse.Namespace) -> int:
    from evaluation.index_locator import load_call_graph
    from evaluation.tracer.build import SCHEMA
    from evaluation.tracer.scoring import make_source_lookup, score_traced

    paths = _locate(args)
    traced = json.loads(Path(args.traced).read_text(encoding="utf-8"))
    if traced.get("schema") != SCHEMA:
        print(f"{args.traced}: expected schema {SCHEMA!r}", file=sys.stderr)
        return 2
    storage = load_call_graph(paths)
    store = open_metadata_store(paths)
    try:
        source_lookup = make_source_lookup(store)
        result = score_traced(
            traced,
            storage.graph,
            source_lookup=source_lookup,
            sample_size=args.sample_size,
            goldens=_load_goldens(Path(args.golden_dir)),
        )
    finally:
        store.close()
    result["report"]["index"] = _index_block(
        paths, traced.get("index", {}).get("chunks", 0)
    )
    result["report"]["traced_file"] = Path(args.traced).as_posix()
    _write_json(Path(args.out), result["report"])
    if args.sample_out:
        _write_json(Path(args.sample_out), result["sample"])
    if args.golden_out_dir:
        for name, payload in result["traced_goldens"].items():
            _write_json(Path(args.golden_out_dir) / name, payload)
    report = result["report"]
    print(
        "denominators: "
        + " ".join(f"{k}={v}" for k, v in report["denominators"].items())
    )
    for tier, row in report["tiers"].items():
        print(
            f"{tier:7s} recall_marginal={row['recall_marginal']:.4f} "
            f"recall_cumulative={row['recall_cumulative']:.4f} "
            f"prec_lb={row['prec_lb']:.4f} prec_lb_cov={row['prec_lb_cov']:.4f} "
            f"|E_t|={row['edges']} unwitnessable={row['unwitnessable']}"
        )
    lt = report["ladder_total"]
    print(
        f"ladder  recall_ladder_total={lt['recall_ladder_total']:.4f} "
        f"prec_lb={lt['prec_lb']:.4f} |E_all|={lt['edges']} "
        f"init_equiv={report['hits_via_init_equivalence']} "
        f"ast_name_only={report['ast_name_only']}"
    )
    print(f"misses: {report['misses']['count']} {report['misses']['taxonomy']}")
    return 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def _add_index_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--project-name", required=True, help="substring of the index dir")
    p.add_argument("--storage", default=None, help="storage root override")
    p.add_argument("--model-slug", default=None, help="disambiguate per-model dirs")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="intersect raw runs and map to chunk ids")
    b.add_argument("--runs", nargs="+", required=True, help="raw run JSON files")
    b.add_argument("--out", default="evaluation/traced_callgraph.json")
    _add_index_args(b)
    b.set_defaults(func=cmd_build)

    s = sub.add_parser("score", help="score resolver tiers against traced edges")
    s.add_argument("--traced", default="evaluation/traced_callgraph.json")
    s.add_argument("--out", default="evaluation/resolver_tier_scores.json")
    s.add_argument("--sample-out", default=None, help="precision hand-label sample")
    s.add_argument("--sample-size", type=int, default=40)
    s.add_argument("--golden-dir", default="evaluation", help="curated goldens")
    s.add_argument(
        "--golden-out-dir",
        default=None,
        help="write caller_golden_traced.json / callee_golden_traced.json here",
    )
    _add_index_args(s)
    s.set_defaults(func=cmd_score)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (IndexNotFoundError, AmbiguousIndexError) as exc:
        print(f"index lookup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
