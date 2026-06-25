"""CLI entry point: run the DSPy agent evaluation harness.

Connects to the already-running code-search HTTP server, runs the DSPy ReAct
agent over the SSCG golden dataset (45 queries, categories A–D), and reports
tool-selection accuracy plus Recall@7/MRR/NDCG.  Results are written to
results/dspy_eval_<ts>.json.

By default evaluates only the held-out **test split** (8 queries) so the
result is a genuine out-of-sample measurement.  Use ``--split all`` for a
full 45-query run (e.g. as a drift check), or ``--split train``/``val`` during
development.

Usage::

    # Default (held-out test split, k=7, concurrency=4):
    .venv/Scripts/python.exe scripts/benchmark/run_dspy_eval.py

    # Full dataset:
    .venv/Scripts/python.exe scripts/benchmark/run_dspy_eval.py --split all

    # Custom:
    .venv/Scripts/python.exe scripts/benchmark/run_dspy_eval.py \\
        --project-path D:/claude-context-local \\
        --split test \\
        --k 7 \\
        --concurrency 4 \\
        --max-iters 6

Prerequisites:
    - The code-search HTTP server is running on port 8765 (start_mcp_http.bat).
    - Project must be indexed: code-search:index_directory or list_projects.
    - Claude Code login active (claude whoami).
    - No ANTHROPIC_API_KEY set (would override subscription OAuth).

Cost: $0 — ClaudeCodeLM bills to the Claude Code Max subscription.
      (Usage counters in the JSON are intentionally zero.)

Baseline for comparison (searcher-only, hybrid mode, 2026-06-08, all 45 queries):
    Recall@7=0.736  MRR=0.797  NDCG@5=0.717
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path


# Ensure the project root is importable when run as a script.
_ROOT = str(Path(__file__).parents[2])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
# Quiet verbose loggers
for _noisy in ("dspy", "httpx", "torch", "httpcore"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="DSPy agent evaluation over the code-search SSCG golden dataset."
    )
    p.add_argument(
        "--project-path",
        default=_ROOT,
        help="Absolute path to the indexed project directory (default: this repo).",
    )
    p.add_argument(
        "--dataset",
        default=None,
        help="Path to a golden-dataset JSON (default: evaluation/golden_dataset.json).",
    )
    p.add_argument(
        "--k",
        type=int,
        default=7,
        help="Recall cut-off (default: 7).",
    )
    p.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Max parallel agent calls (default: 4).",
    )
    p.add_argument(
        "--max-iters",
        type=int,
        default=6,
        help="Max DSPy ReAct iterations per query (default: 6).",
    )
    p.add_argument(
        "--server-url",
        default=None,
        help="Override MCP HTTP server URL (default: http://localhost:8765/mcp).",
    )
    p.add_argument(
        "--model",
        default=None,
        help="Claude model ID (default: DSPY_LM_MODEL env or claude-sonnet-4-6).",
    )
    p.add_argument(
        "--split",
        choices=["train", "val", "test", "all"],
        default="test",
        help=(
            "Dataset split to evaluate: train (27), val (10), test (8, default), "
            "or all (45).  Default 'test' evaluates the held-out split."
        ),
    )
    p.add_argument(
        "--output-dir",
        default=str(Path(_ROOT) / "results"),
        help="Directory for the JSON output file (default: results/).",
    )
    p.add_argument(
        "--tool-names",
        default=None,
        help=(
            "Comma-separated MCP tool names to expose to the agent "
            "(default: search_code,find_connections). "
            "Example: --tool-names search_code,find_connections,find_path,find_similar_code"
        ),
    )
    return p.parse_args()


def _print_per_query_table(per_query: list[dict]) -> None:
    """Print a compact per-query results table to stdout."""
    header = (
        f"{'ID':<6}  {'Cat':<3}  {'R@7':>5}  {'Traj':>5}  {'MRR':>5}  "
        f"{'Tool':>4}  {'ToolUsed'}"
    )
    print(header)
    print("-" * len(header))
    for row in per_query:
        tool_sel = row.get("tool_selection", float("nan"))
        tool_used = ", ".join(row.get("tool_used", [])) or "(none)"
        traj_recall = row.get("trajectory_recall@7", float("nan"))
        print(
            f"{row.get('query_id', '?'):<6}  "
            f"{row.get('category', '?'):<3}  "
            f"{row.get('recall@7', 0.0):>5.3f}  "
            f"{traj_recall:>5.3f}  "
            f"{row.get('mrr', 0.0):>5.3f}  "
            f"{tool_sel:>4.1f}  "
            f"{tool_used}"
        )


def _print_aggregate(agg: dict, k: int, failed: int, total: int) -> None:
    """Print aggregate metrics and pass/fail assessment."""
    print("\n" + "=" * 55)
    print("DSPy AGENT EVAL — AGGREGATE")
    print("=" * 55)
    print(f"  Queries run  : {total - failed}/{total}  (failed: {failed})")
    print(f"  Recall@{k:<2}    : {agg.get(f'recall@{k}', 0.0):.4f}")
    traj_recall = agg.get(f"trajectory_recall@{k}")
    if traj_recall is not None:
        gap = traj_recall - agg.get(f"recall@{k}", 0.0)
        print(f"  Traj recall  : {traj_recall:.4f}  (tool ceiling; gap={gap:+.4f})")
    print(f"  MRR          : {agg.get('mrr', 0.0):.4f}")
    print(f"  NDCG@5       : {agg.get('ndcg@5', 0.0):.4f}")
    print(f"  Hit@7        : {agg.get('hit_rate@7', 0.0):.4f}")
    tool_acc = agg.get("tool_selection_accuracy")
    if tool_acc is not None:
        print(f"  Tool sel acc : {tool_acc:.4f}")
    else:
        print("  Tool sel acc : N/A (no expected_tool ground truth)")
    if "pass_fail" in agg:
        pf = agg["pass_fail"]
        print(
            f"\n  Pass/Fail    : MRR={pf.get('mrr', '?')}  "
            f"Recall@5={pf.get('recall@5', '?')}  "
            f"Hit@5={pf.get('hit_rate@5', '?')}"
        )
    print(
        "\n  Baseline (searcher-only hybrid, 2026-06-08):"
        "\n    Recall@7=0.736  MRR=0.797  NDCG@5=0.717"
    )
    print("\n  Cost: $0 (subscription billing — token counters are intentionally zero)")
    print("=" * 55 + "\n")


def main() -> None:
    args = _parse_args()

    from evaluation.dspy_agent_eval import run_eval  # lazy import (heavy)

    split_display = args.split  # "train"/"val"/"test"/"all"
    split_val: str | None = None if args.split == "all" else args.split

    print(
        f"\n[dspy-eval] project  : {args.project_path}\n"
        f"[dspy-eval] split    : {split_display}\n"
        f"[dspy-eval] k        : {args.k}\n"
        f"[dspy-eval] concurrency: {args.concurrency}\n"
        f"[dspy-eval] max_iters: {args.max_iters}\n"
        "[dspy-eval] Starting agent eval (first query may take ~30-90 s)…\n"
    )

    eval_kwargs: dict = {
        "project_path": args.project_path,
        "split": split_val,
        "k": args.k,
        "concurrency": args.concurrency,
        "max_iters": args.max_iters,
    }
    if args.dataset:
        eval_kwargs["dataset_path"] = args.dataset
    if args.server_url:
        eval_kwargs["server_url"] = args.server_url
    if args.model:
        eval_kwargs["model"] = args.model
    if args.tool_names:
        eval_kwargs["tool_names"] = tuple(args.tool_names.split(","))

    result = asyncio.run(run_eval(**eval_kwargs))

    per_query = result["per_query"]
    agg = result["aggregate"]

    # Per-query table
    print()
    _print_per_query_table(per_query)

    # Aggregate summary
    _print_aggregate(agg, args.k, result["failed_count"], result["total_queries"])

    # Write JSON output
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"dspy_eval_{ts}.json"
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "timestamp": ts,
                "project_path": args.project_path,
                "k": args.k,
                "concurrency": args.concurrency,
                "max_iters": args.max_iters,
                **result,
            },
            fh,
            indent=2,
            default=str,
        )
    print(f"[dspy-eval] Results written to: {output_path}\n")


if __name__ == "__main__":
    main()
