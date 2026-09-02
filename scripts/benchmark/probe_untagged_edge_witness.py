#!/usr/bin/env python3
"""A1': are untagged ``calls`` edges as real as tagged ones? (read-only probe)

A0 (``evaluation/EGO_MEMBERSHIP_PROBE_20260901.md``) found that 84.6% / 86.6%
of traversed call edges resolve below the 0.65 floor, and roughly half of all
traversal events hit edges with no confidence signal at all (the ``untagged``
0.5 fallback in ``graph.graph_storage.edge_confidence``). Every omega/theta
design assumes those edges are worse than tagged ones. This probe joins each
confidence bucket against the execution-witnessed positives from WS-B
(``evaluation/traced_callgraph.json``) and reports the witnessed fraction per
bucket, plus secondary splits of the untagged bucket. Labels are positive-only,
so every ``prec_lb*`` is a lower bound; the verdict compares bounds across
buckets under one identical coverage restriction (caller in EXEC).

    .venv/Scripts/python.exe -m scripts.benchmark.probe_untagged_edge_witness \\
        --project-name claude-context-local \\
        --json-out evaluation/untagged_edge_witness_20260902.json

Deterministic: every emitted list is sorted. No index or config is written.
Exit codes: 0 success, 1 index lookup failure, 2 traced-file schema mismatch.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from evaluation.index_locator import (
    AmbiguousIndexError,
    IndexNotFoundError,
    find_index,
    load_call_graph,
)
from evaluation.probe_harness import write_probe_json


def main(argv: list[str] | None = None) -> int:
    from evaluation.tracer.build import SCHEMA
    from evaluation.tracer.scoring import (
        extract_bucketed_edges,
        extract_static_edges,
        load_traced_edges,
        score_confidence_buckets,
    )

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--project-name", required=True, help="substring of the index dir"
    )
    parser.add_argument("--storage", default=None, help="storage root override")
    parser.add_argument(
        "--model-slug", default=None, help="disambiguate per-model dirs"
    )
    parser.add_argument("--traced", default="evaluation/traced_callgraph.json")
    parser.add_argument(
        "--json-out", default="evaluation/untagged_edge_witness_20260902.json"
    )
    args = parser.parse_args(argv)

    traced_payload = json.loads(Path(args.traced).read_text(encoding="utf-8"))
    if traced_payload.get("schema") != SCHEMA:
        print(f"{args.traced}: expected schema {SCHEMA!r}", file=sys.stderr)
        return 2
    try:
        paths = find_index(
            args.project_name, storage=args.storage, model_slug=args.model_slug
        )
    except (IndexNotFoundError, AmbiguousIndexError) as exc:
        print(f"index lookup failed: {exc}", file=sys.stderr)
        return 1
    graph = load_call_graph(paths).graph
    static = extract_static_edges(graph)
    traced = load_traced_edges(traced_payload, static)
    report = score_confidence_buckets(extract_bucketed_edges(graph), traced)
    report["index"] = {
        "project_dir": str(paths.project_dir),
        "call_graph": str(paths.call_graph),
        "traced_file": Path(args.traced).as_posix(),
    }
    write_probe_json(args.json_out, report)

    print(
        "denominators: "
        + " ".join(f"{k}={v}" for k, v in report["denominators"].items())
    )
    for name, row in report["buckets"].items():
        print(
            f"{name:20s} edges={row['edges']:5d} share={row['edge_share']:.3f} "
            f"cov={row['edges_cov']:5d} prec_lb={row['prec_lb']:.4f} "
            f"prec_lb_cov={row['prec_lb_cov']:.4f} recall={row['recall_marginal']:.4f}"
        )
    print(f"phantom_by_bucket: {report['phantom_by_bucket']}")
    for facet, rows in report["untagged_splits"].items():
        for key, row in rows.items():
            print(
                f"  untagged/{facet}={key:12s} edges={row['edges']:5d} "
                f"cov={row['edges_cov']:5d} prec_lb_cov={row['prec_lb_cov']:.4f}"
            )
    v = report["verdict"]
    print(
        f"verdict: as_reliable_as_ast={v['as_reliable_as_ast']} "
        f"untagged={v['untagged_prec_lb_cov']} tag:exact={v['tag_exact_prec_lb_cov']} "
        f"threshold={v['threshold']} tagging_target={v['tagging_target']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
