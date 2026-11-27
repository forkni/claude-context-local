#!/usr/bin/env python3
"""Make a rust-analyzer SCIP index for an indexed Rust project (ADR-0091 follow-up "E").

``rust-analyzer scip`` is too slow and too large to run inside a reindex (hyprzero:
634 s cold, 16.48 GB peak), so it runs on demand from this command (or the
server launcher's Project Management menu). It writes two files into the
project's storage directory::

    <storage>/scip/index.scip     the SCIP index
    <storage>/scip/manifest.json  format, time, rust-analyzer version, and a
                                  sha256 for every .rs file
    <storage>/scip/refs.sqlite    call references decoded from the index
                                  (search/scip_refs.py), read by the graph build

The graph build uses a SCIP reference only when the caller's file and the
definition's file still have the hash recorded here, so a stale index can never
point an edge at moved lines. A file that changed while rust-analyzer ran is left
out of the manifest. Both files are written to a temporary name first and then
renamed, so a failed run keeps the previous index.

Usage::

    python tools/scip_index.py --path D:/code/my_workspace
    python tools/scip_index.py --path D:/code/my_workspace --digest-only
"""

from __future__ import annotations

import argparse
import functools
import json
import math
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from search.scip_refs import (  # noqa: E402 - after the sys.path insert
    INDEX_NAME,
    MANIFEST_NAME,
    REFS_NAME,
    SCIP_DIRNAME,
    hash_rust_files,
    write_refs_table,
)
from utils.progress import _format_duration  # noqa: E402 - after the sys.path insert


MANIFEST_FORMAT = 1
# rust-analyzer's own output, overwritten on each run (kept after a failure).
LOG_NAME = "rust-analyzer.log"
# How often the timer bar checks whether rust-analyzer has exited.
POLL_SECS = 0.5

Runner = Callable[[list[str], dict[str, str]], int]


def find_rust_analyzer(explicit: str | None = None) -> str | None:
    """The rust-analyzer executable: ``explicit``, then PATH, then ``~/.cargo/bin``."""
    if explicit:
        return explicit if Path(explicit).is_file() or shutil.which(explicit) else None
    found = shutil.which("rust-analyzer")
    if found:
        return found
    cargo_bin = Path.home() / ".cargo" / "bin"
    return shutil.which("rust-analyzer", path=str(cargo_bin))


def _time_left(elapsed: float, estimate_secs: float | None) -> str:
    """``~N min left`` against the estimate, ``over estimate`` past it, else empty."""
    if estimate_secs is None:
        return ""
    remaining = estimate_secs - elapsed
    if remaining <= 0:
        return "over estimate"
    return f"~{math.ceil(remaining / 60)} min left"


def _default_runner(
    cmd: list[str],
    env: dict[str, str],
    log_path: Path | None = None,
    estimate_secs: float | None = None,
) -> int:
    """Run ``cmd``; with ``log_path``, its stdout and stderr go to that file.

    rust-analyzer writes thousands of known-bug lines during ``scip`` (ADR-0092),
    so the console gets a summary (:func:`summarize_rust_analyzer_log`) instead.
    While it runs, a terminal shows a timer bar: rust-analyzer reports no
    progress, so the bar fills against ``estimate_secs`` (the last run's time);
    with no estimate the bar stays empty and only the elapsed time moves.

    The columns and colors match the chunking and embedding bars
    (``search/parallel_chunker.py``, ``embeddings/embedder.py``): spinner,
    description, bar, percentage, then plain text in parentheses. The bar
    never pulses, stops at 99% while rust-analyzer still runs past the
    estimate, and turns green at 100% when it exits with code 0.
    """
    if log_path is None:
        return subprocess.run(cmd, env=env, check=False).returncode
    from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn

    from utils.console import get_progress_console, get_progress_spinner

    console = get_progress_console()
    columns = [
        get_progress_spinner(console),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
    ]
    if estimate_secs is not None:
        columns.append(TaskProgressColumn())
    columns.append(TextColumn("({task.fields[timing]})"))
    # A total keeps the bar out of rich's pulse animation, which has its own
    # colors. With no estimate, 1 "unit" that is never reached = an empty bar.
    total = estimate_secs if estimate_secs is not None else 1.0
    ceiling = total * 0.99
    with log_path.open("wb") as log:
        proc = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            with Progress(
                *columns,
                console=console,
                transient=False,
                disable=not console.is_terminal,
            ) as progress:
                task = progress.add_task(
                    "rust-analyzer scip...",
                    total=total,
                    timing=_timing(0.0, estimate_secs),
                )
                started = time.perf_counter()
                while proc.poll() is None:
                    elapsed = time.perf_counter() - started
                    progress.update(
                        task,
                        completed=min(elapsed, ceiling) if estimate_secs else 0.0,
                        timing=_timing(elapsed, estimate_secs),
                    )
                    time.sleep(POLL_SECS)
                elapsed = time.perf_counter() - started
                progress.update(
                    task,
                    completed=total if proc.returncode == 0 else None,
                    timing=_format_duration(elapsed),
                )
        except BaseException:
            proc.kill()
            proc.wait()
            raise
    return proc.returncode


def _timing(elapsed: float, estimate_secs: float | None) -> str:
    """Text for the bar's last column: ``52s, ~12 min left`` or just ``52s``."""
    left = _time_left(elapsed, estimate_secs)
    duration = _format_duration(elapsed)
    return f"{duration}, {left}" if left else duration


def _last_run(out_dir: Path) -> tuple[float, str] | None:
    """``(wall_secs, local date)`` of the previous run, from its manifest; else None."""
    try:
        manifest = json.loads((out_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
        wall = float(manifest["wall_secs"])
        created = datetime.fromisoformat(manifest["created"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if wall <= 0:
        return None
    return wall, created.astimezone().strftime("%Y-%m-%d")


def summarize_rust_analyzer_log(log_path: Path) -> dict[str, int]:
    """Count rust-analyzer's two known-bug messages in ``log_path`` (0 if no log).

    ``outside_document``: "definition ... should have been in an SCIP document";
    ``duplicate_symbols``: "Duplicate symbol:" entries. Neither loses a function
    definition from the reference table (ADR-0092).
    """
    counts = {"outside_document": 0, "duplicate_symbols": 0}
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return counts
    for line in text.splitlines():
        if "should have been in an SCIP document" in line:
            counts["outside_document"] += 1
        elif line.lstrip().startswith("Duplicate symbol:"):
            counts["duplicate_symbols"] += 1
    return counts


def _log_tail(log_path: Path, lines: int = 20) -> list[str]:
    """The last ``lines`` lines of ``log_path``; empty if it cannot be read."""
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return text.splitlines()[-lines:]


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
    runner: Runner | None = None,
    version: str | None = None,
    decode: bool = True,
    estimate_secs: float | None = None,
) -> dict:
    """Run ``rust-analyzer scip`` on ``project`` and write the index and manifest.

    Args:
        project: Cargo workspace root (holds ``Cargo.toml``).
        out_dir: Directory for ``index.scip`` and ``manifest.json``.
        rust_analyzer: rust-analyzer executable.
        target_dir: ``CARGO_TARGET_DIR`` for the build scripts and proc macros
            rust-analyzer compiles; None leaves the environment unchanged.
        runner: Runs the command and returns its exit code (tests inject one).
            None runs it with its output in ``<out_dir>/rust-analyzer.log``.
        version: rust-analyzer version text; None asks the executable.
        decode: Also write the reference table (``refs.sqlite``) from the index.
        estimate_secs: Expected run time for the default runner's timer bar
            (the last run's ``wall_secs``); None shows elapsed time only.

    The three output files are written under temporary names and renamed only
    after all of them exist: index, then table, then the manifest last, so the
    manifest's hashes never describe files from an older run. On any failure the
    temporary files are removed and the previous output stays.

    Returns:
        The manifest that was written.

    Raises:
        FileNotFoundError: ``project`` has no ``Cargo.toml``.
        RuntimeError: rust-analyzer failed or wrote no index.
        ValueError, IndexError: the index could not be decoded.
    """
    if not (project / "Cargo.toml").is_file():
        raise FileNotFoundError(f"no Cargo.toml in {project}")
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_index = out_dir / f"{INDEX_NAME}.tmp"
    tmp_refs = out_dir / f"{REFS_NAME}.new"
    tmp_manifest = out_dir / f"{MANIFEST_NAME}.tmp"
    temporaries = (tmp_index, tmp_refs, tmp_manifest)
    for tmp in temporaries:
        tmp.unlink(missing_ok=True)

    before = hash_rust_files(project)
    env = dict(os.environ)
    if target_dir is not None:
        env["CARGO_TARGET_DIR"] = str(target_dir)
    cmd = [rust_analyzer, "scip", str(project), "--output", str(tmp_index)]
    if runner is None:
        runner = functools.partial(
            _default_runner, log_path=out_dir / LOG_NAME, estimate_secs=estimate_secs
        )
    started = time.perf_counter()
    code = runner(cmd, env)
    wall = time.perf_counter() - started
    if code != 0 or not tmp_index.is_file():
        tmp_index.unlink(missing_ok=True)
        raise RuntimeError(f"rust-analyzer scip exited {code} after {wall:.0f} s")
    try:
        manifest = _finish(
            project, out_dir, rust_analyzer, before, wall, version, decode, temporaries
        )
    except BaseException:
        for tmp in temporaries:
            tmp.unlink(missing_ok=True)
        raise
    return manifest


def _finish(
    project: Path,
    out_dir: Path,
    rust_analyzer: str,
    before: dict[str, str],
    wall: float,
    version: str | None,
    decode: bool,
    temporaries: tuple[Path, Path, Path],
) -> dict:
    """Hash again, decode, write the manifest, then rename all outputs into place."""
    tmp_index, tmp_refs, tmp_manifest = temporaries
    after = hash_rust_files(project)

    changed = sorted(
        p for p in before.keys() | after.keys() if before.get(p) != after.get(p)
    )
    files = {p: h for p, h in sorted(after.items()) if p not in changed}
    refs = write_refs_table(tmp_index, tmp_refs) if decode else None
    manifest = {
        "format": MANIFEST_FORMAT,
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "project_path": str(project),
        "rust_analyzer": version if version is not None else _version(rust_analyzer),
        "wall_secs": round(wall, 1),
        "index_bytes": tmp_index.stat().st_size,
        "changed_during_run": changed,
        "refs": refs,
        "files": files,
    }
    tmp_manifest.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    os.replace(tmp_index, out_dir / INDEX_NAME)
    if decode:
        os.replace(tmp_refs, out_dir / REFS_NAME)
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
    parser.add_argument(
        "--digest-only",
        action="store_true",
        help="Rebuild refs.sqlite from the existing index.scip; no rust-analyzer run",
    )
    args = parser.parse_args(argv)

    project = Path(args.path).resolve()
    if not (project / "Cargo.toml").is_file():
        print(f"[ERROR] No Cargo.toml in {project}: SCIP needs a Cargo workspace root.")
        return 2
    if args.digest_only:
        return _digest_only(project)
    rust_analyzer = find_rust_analyzer(args.rust_analyzer)
    if rust_analyzer is None and args.rust_analyzer:
        print(
            f"[ERROR] --rust-analyzer {args.rust_analyzer} is not a file or a command on PATH."
        )
        return 2
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
    log_path = out_dir / LOG_NAME
    print(f"[INFO] rust-analyzer log: {log_path}")
    last = _last_run(out_dir)
    if last is not None:
        wall, day = last
        print(
            f"[INFO] Last run: {_format_duration(wall)} on {day}, "
            f"so expect about {math.ceil(wall / 60)} min."
        )
    print(
        "[INFO] Running rust-analyzer scip (large workspaces: ~10 min, ~16 GB RAM)..."
    )
    try:
        manifest = make_scip_index(
            project,
            out_dir,
            rust_analyzer,
            target_dir=target_dir,
            estimate_secs=last[0] if last is not None else None,
        )
    except (FileNotFoundError, RuntimeError, OSError, ValueError, IndexError) as exc:
        print(f"[ERROR] {exc}")
        if isinstance(exc, RuntimeError):
            tail = _log_tail(log_path)
            if tail:
                print(f"[ERROR] Last {len(tail)} lines of {log_path}:")
                for line in tail:
                    print(f"  {line}")
        return 1
    print(
        f"[OK] SCIP index: {manifest['index_bytes'] / 1e6:.1f} MB, "
        f"{len(manifest['files'])} .rs files hashed, {manifest['wall_secs']:.0f} s"
    )
    noise = summarize_rust_analyzer_log(log_path)
    if any(noise.values()):
        print(
            f"[INFO] rust-analyzer reported {noise['outside_document']} definitions "
            f"outside a SCIP document and {noise['duplicate_symbols']} duplicate "
            "symbols (known rust-analyzer issues; call edges are not affected)"
        )
    if manifest["changed_during_run"]:
        print(
            f"[WARN] {len(manifest['changed_during_run'])} .rs file(s) changed during the run "
            "and are left out; rerun to cover them."
        )
    refs = manifest.get("refs") or {}
    print(
        f"[OK] Reference table: {refs.get('symbols', 0)} functions "
        f"({refs.get('external', 0)} external), {refs.get('refs', 0)} references"
    )
    print(
        "[INFO] Set call_graph.rust_scip to true, then reindex, to use it in the call graph."
    )
    return 0


def _digest_only(project: Path) -> int:
    """Rebuild ``refs.sqlite`` from the stored index and record it in the manifest.

    Refuses without a manifest: the table is only usable with the hashes of the
    run that made the index.
    """
    out_dir = _storage_scip_dir(project)
    if (
        out_dir is None
        or not (out_dir / INDEX_NAME).is_file()
        or not (out_dir / MANIFEST_NAME).is_file()
    ):
        print(
            f"[ERROR] No SCIP index and manifest for {project}. "
            "Run without --digest-only first."
        )
        return 2
    tmp_manifest = out_dir / f"{MANIFEST_NAME}.tmp"
    try:
        manifest = json.loads((out_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
        refs = write_refs_table(out_dir / INDEX_NAME, out_dir / REFS_NAME)
        manifest["refs"] = refs
        tmp_manifest.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        os.replace(tmp_manifest, out_dir / MANIFEST_NAME)
    except (OSError, ValueError, IndexError) as exc:
        tmp_manifest.unlink(missing_ok=True)
        print(f"[ERROR] {exc}")
        return 1
    print(
        f"[OK] Reference table: {refs['symbols']} functions ({refs['external']} external), "
        f"{refs['refs']} references -> {out_dir / REFS_NAME}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
