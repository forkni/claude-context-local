"""The ``search`` package loads its heavy members (torch) only on first use."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _run(code: str) -> str:
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    return result.stdout.strip()


def test_index_freshness_import_leaves_torch_unloaded() -> None:
    """The launcher's index check must not pay for torch (about 1.2 s)."""
    out = _run(
        "import sys; import mcp_server.index_freshness; print('torch' in sys.modules)"
    )
    assert out == "False"


def test_heavy_names_still_import_from_the_package_root() -> None:
    out = _run(
        "import search\n"
        "from search import GPUMemoryMonitor, MultiHopSearcher, RerankingEngine\n"
        "from search.multi_hop_searcher import MultiHopSearcher as M\n"
        "print(MultiHopSearcher is M, set(search.__all__) <= set(dir(search)))"
    )
    assert out == "True True"
