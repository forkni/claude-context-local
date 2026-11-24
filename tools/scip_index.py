#!/usr/bin/env python3
"""Make a rust-analyzer SCIP index for an indexed Rust project (ADR-0091 follow-up "E").

``rust-analyzer scip`` is too slow and too large to run inside a reindex (hyprzero:
634 s cold, 16.48 GB peak), so it runs on demand from this command (or the
server launcher's Project Management menu). It writes two files into the
project's storage directory::

    <storage>/scip/index.scip     the SCIP index
    <storage>/scip/manifest.json  format, time, rust-analyzer version, and a
                                  sha256 for every .rs file

The graph build uses a SCIP reference only when the caller's file and the
definition's file still have the hash recorded here, so a stale index can never
point an edge at moved lines. A file that changed while rust-analyzer ran is left
out of the manifest. Both files are written to a temporary name first and then
renamed, so a failed run keeps the previous index.

Usage::

    python tools/scip_index.py --path D:/code/my_workspace
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

MANIFEST_FORMAT = 1
SCIP_DIRNAME = "scip"
INDEX_NAME = "index.scip"
MANIFEST_NAME = "manifest.json"
# Directories that never hold project sources: build output and VCS data.
_SKIP_DIRS = frozenset({"target", ".git", "node_modules", ".venv"})

Runner = Callable[[list[str], dict[str, str]], int]


def hash_rust_files(root: Path) -> dict[str, str]:
    """``{relative posix path: sha256 hex}`` for every ``.rs`` file under ``root``.

    Skips build output and VCS directories (``target``, ``.git`` and similar)
    at any depth.
    """
    hashes: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS)
        for name in sorted(filenames):
            if not name.endswith(".rs"):
                continue
            path = Path(dirpath) / name
            try:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
            hashes[path.relative_to(root).as_posix()] = digest
    return hashes


def find_rust_analyzer(explicit: str | None = None) -> str | None:
    """The rust-analyzer executable: ``explicit``, then PATH, then ``~/.cargo/bin``."""
    if explicit:
        return explicit if Path(explicit).is_file() or shutil.which(explicit) else None
    found = shutil.which("rust-analyzer")
    if found:
        return found
    cargo_bin = Path.home() / ".cargo" / "bin"
    return shutil.which("rust-analyzer", path=str(cargo_bin))


def _default_runner(cmd: list[str], env: dict[str, str]) -> int:
    return subprocess.run(cmd, env=env, check=False).returncode


def _version(rust_analyzer: str) -> str:
    try:
        out = subprocess.run(
            [rust_analyzer, "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    return out.stdout.strip() or "unknown"


def make_scip_index(
    project: Path,
    out_dir: Path,
    rust_analyzer: str,
    *,
    target_dir: Path | None = None,
    runner: Runner = _default_runner,
    version: str | None = None,
) -> dict:
    """Run ``rust-analyzer scip`` on ``project`` and write the index and manifest.

    Args:
        project: Cargo workspace root (holds ``Cargo.toml``).
        out_dir: Directory for ``index.scip`` and ``manifest.json``.
        rust_analyzer: rust-analyzer executable.
        target_dir: ``CARGO_TARGET_DIR`` for the build scripts and proc macros
            rust-analyzer compiles; None leaves the environment unchanged.
        runner: Runs the command and returns its exit code (tests inject one).
        version: rust-analyzer version text; None asks the executable.

    Returns:
        The manifest that was written.

    Raises:
        FileNotFoundError: ``project`` has no ``Cargo.toml``.
        RuntimeError: rust-analyzer failed or wrote no index.
    """
    if not (project / "Cargo.toml").is_file():
        raise FileNotFoundError(f"no Cargo.toml in {project}")
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_index = out_dir / f"{INDEX_NAME}.tmp"
    tmp_index.unlink(missing_ok=True)

    before = hash_rust_files(project)
    env = dict(os.environ)
    if target_dir is not None:
        env["CARGO_TARGET_DIR"] = str(target_dir)
    cmd = [rust_analyzer, "scip", str(project), "--output", str(tmp_index)]
    started = time.perf_counter()
    code = runner(cmd, env)
    wall = time.perf_counter() - started
    if code != 0 or not tmp_index.is_file():
        tmp_index.unlink(missing_ok=True)
        raise RuntimeError(f"rust-analyzer scip exited {code} after {wall:.0f} s")
    after = hash_rust_files(project)

    changed = sorted(
        p for p in before.keys() | after.keys() if before.get(p) != after.get(p)
    )
    files = {p: h for p, h in sorted(after.items()) if p not in changed}
    manifest = {
        "format": MANIFEST_FORMAT,
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "project_path": str(project),
        "rust_analyzer": version if version is not None else _version(rust_analyzer),
        "wall_secs": round(wall, 1),
        "index_bytes": tmp_index.stat().st_size,
        "changed_during_run": changed,
        "files": files,
    }
    tmp_manifest = out_dir / f"{MANIFEST_NAME}.tmp"
    tmp_manifest.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    os.replace(tmp_index, out_dir / INDEX_NAME)
    os.replace(tmp_manifest, out_dir / MANIFEST_NAME)
    return manifest


def _storage_scip_dir(project: Path) -> Path | None:
    """``<storage>/scip`` for an already-indexed project, else None.

    Read-only on purpose: ``get_project_storage_dir`` creates a storage folder
    for an unknown project, which this command must never do.
    """
    from mcp_server.storage_manager import get_storage_dir
    from search.config import get_search_config

    model = get_search_config().embedding.model_name
    wanted = os.path.normcase(str(project))
    for info_file in sorted(
        (get_storage_dir() / "projects").glob("*/project_info.json")
    ):
        try:
            info = json.loads(info_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        path = info.get("project_path")
        if (
            path
            and os.path.normcase(str(Path(path).resolve())) == wanted
            and info.get("embedding_model") == model
        ):
            return info_file.parent / SCIP_DIRNAME
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--path", required=True, help="Cargo workspace root of an indexed project"
    )
    parser.add_argument(
        "--rust-analyzer", help="rust-analyzer executable (default: PATH, ~/.cargo/bin)"
    )
    parser.add_argument(
        "--target-dir",
        help="CARGO_TARGET_DIR for rust-analyzer's build (default: <storage>/scip/target, "
        "so the project's own target/ is not locked)",
    )
    args = parser.parse_args(argv)

    project = Path(args.path).resolve()
    if not (project / "Cargo.toml").is_file():
        print(f"[ERROR] No Cargo.toml in {project}: SCIP needs a Cargo workspace root.")
        return 2
    rust_analyzer = find_rust_analyzer(args.rust_analyzer)
    if rust_analyzer is None:
        print(
            "[ERROR] rust-analyzer not found. Install it: rustup component add rust-analyzer"
        )
        return 2
    out_dir = _storage_scip_dir(project)
    if out_dir is None:
        print(
            f"[ERROR] {project} is not indexed yet. Index it first, then make the SCIP index."
        )
        return 2
    target_dir = Path(args.target_dir) if args.target_dir else out_dir / "target"

    print(f"[INFO] Project: {project}")
    print(f"[INFO] rust-analyzer: {rust_analyzer}")
    print(f"[INFO] Output: {out_dir / INDEX_NAME}")
    print(
        "[INFO] Running rust-analyzer scip (large workspaces: ~10 min, ~16 GB RAM)..."
    )
    try:
        manifest = make_scip_index(
            project, out_dir, rust_analyzer, target_dir=target_dir
        )
    except (FileNotFoundError, RuntimeError, OSError) as exc:
        print(f"[ERROR] {exc}")
        return 1
    print(
        f"[OK] SCIP index: {manifest['index_bytes'] / 1e6:.1f} MB, "
        f"{len(manifest['files'])} .rs files hashed, {manifest['wall_secs']:.0f} s"
    )
    if manifest["changed_during_run"]:
        print(
            f"[WARN] {len(manifest['changed_during_run'])} .rs file(s) changed during the run "
            "and are left out; rerun to cover them."
        )
    print(
        "[INFO] The graph build does not read this index yet (planned: SCIP call tier)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
