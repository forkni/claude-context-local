"""Live demo: DSPy ReAct agent answering questions via code-search MCP tools.

Runs entirely on the Claude Code Max subscription — no ANTHROPIC_API_KEY.
The agent connects to the already-running code-search HTTP server (port 8765),
calls search_code / find_connections as needed, and prints the answer with its
full trajectory.

Usage::

    # Default question (FAISS class location):
    .venv/Scripts/python.exe scripts/dspy_mcp_demo.py

    # Custom question:
    .venv/Scripts/python.exe scripts/dspy_mcp_demo.py "How does hybrid search work?"

Prerequisites:
    - The code-search HTTP server is running on port 8765.
      Start it with start_mcp_http.bat if needed.
    - Repo indexed: use /mcp -> code-search:index_directory or check list_projects
    - Claude Code login active (claude whoami)
    - No ANTHROPIC_API_KEY set (would hijack the subscription)
"""

import asyncio
import logging
import sys
from pathlib import Path


# Make sure the project root is on sys.path when run directly.
_ROOT = str(Path(__file__).parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
# Quiet the very chatty DSPy / torch / MCP loggers.
logging.getLogger("dspy").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("torch").setLevel(logging.WARNING)


async def main(question: str) -> None:
    from utils.dspy_mcp import run_code_search_agent

    project_path = _ROOT
    print(f"\n[demo] question : {question!r}")
    print(f"[demo] project  : {project_path}")
    print("[demo] tools    : search_code, find_connections")
    print("[demo] Starting agent (first run may take ~30-90 s for model load)…\n")

    result = await run_code_search_agent(
        question,
        project_path=project_path,
        tool_names=("search_code", "find_connections"),
        max_iters=6,
    )

    print("\n" + "=" * 60)
    print(f"ANSWER: {result.answer}")
    print("=" * 60)

    trajectory = getattr(result, "trajectory", None)
    if trajectory:
        print("\n--- ReAct trajectory ---")
        for key, value in trajectory.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    q = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else (
            "Where is the FAISS vector index class defined? "
            "Return the file path and class name."
        )
    )
    asyncio.run(main(q))
