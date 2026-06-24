"""CLI entry point: run GEPA to optimise the CodeNavQA DSPy signature.

Uses ``dspy.GEPA`` (reflective prompt evolution) to discover improved
instructions for the ``CodeNavQA`` signature in
``evaluation/dspy_agent_eval.py``.  The optimised instructions are printed to
stdout so you can review them before porting them back into the source code.

Artifacts (program JSON + stats JSON) are written to a gitignored ``results/``
directory — they are **not** committed automatically.  After the run:

1. Review the printed "Discovered instruction" and compare it to the hand-written
   seed in ``evaluation/dspy_agent_eval.py``.
2. If the GEPA instruction beats the seed: manually port it into
   ``CodeNavQA`` (docstring + ``relevant_chunk_ids`` desc), then re-run
   ``run_dspy_eval.py`` to confirm the lift, then commit.
3. If the seed is already optimal: no change needed.

Usage::

    # Default (light budget, opus reflection, sonnet rollouts):
    .venv/Scripts/python.exe scripts/benchmark/run_dspy_gepa.py \\
        --project-path D:/claude-context-local

    # Custom budget / model:
    .venv/Scripts/python.exe scripts/benchmark/run_dspy_gepa.py \\
        --project-path D:/claude-context-local \\
        --budget medium \\
        --reflection-model claude-opus-4-8 \\
        --model claude-sonnet-4-6

Prerequisites:
    - The code-search HTTP server is running on port 8765 (start_mcp_http.bat).
    - Project must be indexed: code-search:index_directory or list_projects.
    - Claude Code login active (claude whoami).
    - NO ANTHROPIC_API_KEY set (would override subscription OAuth).
    - Recommended: CLAUDE_CODE_OAUTH_TOKEN set for unattended runs.
    - Recommended: CLAUDE_CODE_RETRY_WATCHDOG=1 for long GEPA runs.

Cost: $0 — ClaudeCodeLM bills to the Claude Code Max subscription.

Expected runtime: light budget ~ 10-60 min depending on server + model latency.
"""

import argparse
import json
import logging
import os
import sys
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
# Quiet verbose loggers.
for _noisy in ("dspy", "httpx", "torch", "httpcore"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run GEPA to optimise the CodeNavQA DSPy signature."
    )
    p.add_argument(
        "--project-path",
        default=_ROOT,
        help="Absolute path to the indexed project directory (default: this repo).",
    )
    p.add_argument(
        "--budget",
        choices=["light", "medium", "heavy"],
        default="light",
        help=(
            "GEPA auto budget preset: "
            "light=6, medium=12, heavy=18 candidate evaluations. "
            "Default: light."
        ),
    )
    p.add_argument(
        "--reflection-model",
        default="claude-opus-4-8",
        help=(
            "Claude model for GEPA reflection (instruction proposal). "
            "Default: claude-opus-4-8."
        ),
    )
    p.add_argument(
        "--model",
        default=None,
        help=(
            "Claude model for rollouts (default: DSPY_LM_MODEL env or "
            "claude-sonnet-4-6)."
        ),
    )
    p.add_argument(
        "--num-threads",
        type=int,
        default=4,
        help=(
            "GEPA worker threads (default: 4). Keep ≤ 4; MCP tool I/O "
            "is serialised on the single session."
        ),
    )
    p.add_argument(
        "--max-iters",
        type=int,
        default=6,
        help="Max DSPy ReAct iterations per rollout (default: 6).",
    )
    p.add_argument(
        "--output-dir",
        default=str(Path(_ROOT) / "results"),
        help="Directory for artifacts (default: results/).",
    )
    p.add_argument(
        "--server-url",
        default=None,
        help="Override MCP HTTP server URL (default: http://localhost:8765/mcp).",
    )
    return p.parse_args()


def _print_prereq_banner(args: argparse.Namespace) -> None:
    """Print a prerequisites checklist before starting the long GEPA run."""
    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_oauth = bool(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"))
    has_watchdog = bool(os.environ.get("CLAUDE_CODE_RETRY_WATCHDOG"))

    print("\n" + "=" * 65)
    print("GEPA OPTIMISATION — PREREQUISITES")
    print("=" * 65)
    print(f"  Project path    : {args.project_path}")
    print(f"  Budget          : {args.budget}")
    print(f"  Rollout model   : {args.model or 'DSPY_LM_MODEL or claude-sonnet-4-6'}")
    print(f"  Reflection model: {args.reflection_model}")
    print(f"  Num threads     : {args.num_threads}")
    print(f"  Max iters       : {args.max_iters}")
    print(f"  Output dir      : {args.output_dir}")
    print()
    print("  Checklist:")
    print("    [ ] MCP server running on port 8765 (start_mcp_http.bat)")
    print("    [ ] Project indexed (code-search:list_projects)")
    print("    [ ] Claude Code login active (claude whoami)")
    if has_api_key:
        print("  [WARN] ANTHROPIC_API_KEY is set — this OVERRIDES subscription OAuth!")
        print(
            "         Unset it to ensure subscription billing: unset ANTHROPIC_API_KEY"
        )
    else:
        print("    [OK] ANTHROPIC_API_KEY not set — subscription billing active")
    if has_oauth:
        print("    [OK] CLAUDE_CODE_OAUTH_TOKEN set — unattended auth available")
    else:
        print("    [  ] CLAUDE_CODE_OAUTH_TOKEN not set (interactive auth used)")
    if has_watchdog:
        print("    [OK] CLAUDE_CODE_RETRY_WATCHDOG set — long-run retry enabled")
    else:
        print("    [  ] CLAUDE_CODE_RETRY_WATCHDOG not set (recommended for long runs)")

    print()
    print(
        "  NOTE: This is in-sample prompt discovery (trainset = valset = 13 queries)."
    )
    print(
        "  Validate the result by re-running run_dspy_eval.py after porting "
        "the\n  discovered instruction into CodeNavQA."
    )
    print("=" * 65 + "\n")


def main() -> None:
    args = _parse_args()
    _print_prereq_banner(args)

    from evaluation.dspy_gepa_optimize import run_gepa_optimization  # lazy import

    kwargs: dict = {
        "budget": args.budget,
        "reflection_model": args.reflection_model,
        "rollout_model": args.model,
        "num_threads": args.num_threads,
        "max_iters": args.max_iters,
        "output_dir": Path(args.output_dir),
    }
    if args.server_url:
        kwargs["server_url"] = args.server_url

    print("[gepa] Starting optimisation (first call may take 60–120 s)…\n")
    result = run_gepa_optimization(args.project_path, **kwargs)

    # Print summary.
    print("\n" + "=" * 65)
    print("GEPA OPTIMISATION — RESULT")
    print("=" * 65)
    print(f"  Seed Recall@7   : {result['seed_score']:.4f}")
    print(f"  Best Recall@7   : {result['best_score']:.4f}")
    lift = result["best_score"] - result["seed_score"]
    print(f"  Lift            : {lift:+.4f}")
    print()
    print("  Discovered instruction:")
    print("  " + "-" * 61)
    for line in (result["optimized_instruction"] or "(not extracted)").splitlines():
        print(f"  {line}")
    print("  " + "-" * 61)
    print()
    print("  Artifacts:")
    for path in result["artifact_paths"]:
        print(f"    {path}")
    print()
    print("  Next steps:")
    print("    1. Review the discovered instruction above.")
    if result["best_score"] > result["seed_score"]:
        print("    2. Instruction BEATS the seed — port it into CodeNavQA in")
        print(
            "       evaluation/dspy_agent_eval.py (docstring + relevant_chunk_ids desc)."
        )
        print("    3. Re-run run_dspy_eval.py to confirm the lift.")
        print("    4. Commit: feat: adopt GEPA-discovered CodeNavQA instruction")
    else:
        print("    2. Instruction did NOT beat the seed — hand-written instruction")
        print("       is already optimal (or try --budget medium for more candidates).")
    print("=" * 65 + "\n")

    # Also write a compact JSON summary to stdout-adjacent location.
    summary_path = Path(args.output_dir) / "gepa" / "latest_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, default=str)
    print(f"[gepa] Summary written to: {summary_path}\n")


if __name__ == "__main__":
    main()
