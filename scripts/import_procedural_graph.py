"""Import a producer-authored Procedural Graph seed into the local store.

Standalone operator entry point for ADR-0074: the only supported way to load
a seed document (produced by ``TD_Glossary_tox``) into
``<storage_dir>/procedural_graphs/``. Deliberately does **not** import
``mcp_server.storage_manager.get_storage_dir`` -- that import pulls in
PyTorch and measured 10.4s on this machine, which is unacceptable for a
one-shot CLI script. Instead this script re-implements the *lookup* half of
``get_storage_dir`` standalone (matching ``scripts/list_projects_parseable.py``
and ``scripts/list_projects_display.py``, both read-only) plus a
dependency-free subset of ``validate_storage_path``'s safety checks --
refusing the home directory, a filesystem root, or a path under a
project-root marker. This is not full replication: it skips nothing the
server itself checks at those three cases, but unlike the server (which
falls back silently to the default on an unsafe path) this script exits
with an error pointing at ``--storage-dir``, since a bad write destination
deserves a loud failure. ``--storage-dir`` is an explicit operator choice
and is used as-is, unguarded.

Usage:
    .venv/Scripts/python.exe scripts/import_procedural_graph.py \
        tests/fixtures/pg/network_layout_seed.json
    .venv/Scripts/python.exe scripts/import_procedural_graph.py \
        tests/fixtures/pg/network_layout_seed.json --name network_layout__cand3 --force
"""

import argparse
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from graph.procedural_graph import (  # noqa: E402
    ProceduralGraphError,
    ProceduralGraphStore,
)


# Mirrors mcp_server/storage_manager.py::_PROJECT_MARKERS -- that module is
# the source of truth; keep this tuple in sync with it by hand.
_PROJECT_MARKERS = (
    ".git",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
)


def _validate_storage_path(path: Path) -> tuple[bool, str]:
    """Dependency-free subset of
    ``mcp_server.storage_manager.py::validate_storage_path`` -- that
    function is the source of truth; this re-implements its two checks
    without the module's PyTorch-heavy import chain (see module docstring).
    """
    p = path.resolve()
    home = Path.home()

    if p == home or p == Path(p.anchor):
        return False, f"refusing home dir or filesystem root: {p}"

    for ancestor in (p, *p.parents):
        if ancestor == home or ancestor == ancestor.parent:
            break
        for marker in _PROJECT_MARKERS:
            if (ancestor / marker).exists():
                return (
                    False,
                    f"path is inside a project tree ({marker} found at {ancestor})",
                )

    return True, "ok"


def _default_storage_dir() -> Path:
    """Re-implements the lookup half of
    ``mcp_server.storage_manager.get_storage_dir()`` plus a subset of its
    safety checks, without importing it (see module docstring for why).
    Unlike the server, which falls back silently to the default on an
    unsafe path, this exits loudly -- a write landing somewhere unexpected
    is worse than a script that refuses to run.
    """
    storage_path = os.getenv(
        "CODE_SEARCH_STORAGE", str(Path.home() / ".claude_code_search")
    )
    candidate = Path(storage_path).expanduser()
    ok, reason = _validate_storage_path(candidate)
    if not ok:
        print(
            f"CODE_SEARCH_STORAGE={storage_path!r} is unsafe: {reason}", file=sys.stderr
        )
        print("Pass --storage-dir to choose an explicit location.", file=sys.stderr)
        sys.exit(1)
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "seed", type=Path, help="Path to a Procedural Graph seed JSON document"
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Stored name (default: the seed's own 'name' field)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing graph of the same name",
    )
    parser.add_argument(
        "--storage-dir",
        type=Path,
        default=None,
        help="Base storage dir (default: $CODE_SEARCH_STORAGE or ~/.claude_code_search)",
    )
    args = parser.parse_args()

    base_dir = (
        args.storage_dir if args.storage_dir is not None else _default_storage_dir()
    )
    store = ProceduralGraphStore(base_dir / "procedural_graphs")

    try:
        stored_name = store.import_seed(args.seed, name=args.name, force=args.force)
    except ProceduralGraphError as exc:
        print(f"invalid procedural graph seed: {args.seed}", file=sys.stderr)
        for error in exc.errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    graph = store.load(stored_name)
    dest = store.path_for(stored_name)
    # hops=1 is a no-op here: extract(None, ...) always returns every
    # transition regardless of hops (see ProceduralGraph.extract).
    edge_count = len(graph.extract(None, 1))
    print(f"imported {stored_name!r} -> {dest}")
    print(f"{len(graph.node_ids)} nodes, {edge_count} edges")


if __name__ == "__main__":
    main()
