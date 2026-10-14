#!/usr/bin/env python3
"""Parse-recall measurement for C-family chunking (ADR-0087).

`[PARSE_WARN]` only counts ERROR lines that land in no chunk. Most silently
dropped content never touches an ERROR node: it sits inside an `extern "C"`
block, a namespace, or a declaration whose struct got chunked, and the
preamble collector skips the whole root child. This harness measures the
whole file instead, through the real `TreeSitterChunker.parse_file` ->
`chunk_parsed` path.

Per file it reports:
    - ERROR lines (distinct lines under ERROR nodes) and the non-blank ones
      no chunk covers (the PARSE_WARN view);
    - dropped code lines: non-blank, non-comment lines in no chunk span.
      `#if/#ifdef/#ifndef/#elif/#else/#endif` lines and lone-brace trivia
      are excluded; other directives (`#define`, `#include`) are counted
      separately. Dropped code lines are bucketed by enclosing root node;
    - dropped comment lines. A comment block directly above a chunk that
      carries a `docstring` counts as covered;
    - chunk count and the multiset of `(node_type, name)` definitions.

Usage:
    .venv/Scripts/python.exe -m scripts.benchmark.measure_parse_recall ROOT \\
        --json logs/parse_recall_baseline.json
    .venv/Scripts/python.exe -m scripts.benchmark.measure_parse_recall ROOT \\
        --compare logs/parse_recall_baseline.json --index-filter
"""

import argparse
import json
import logging
import os
import re
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from chunking.language_registry import EXT_TO_LANGUAGE
from chunking.multi_language_chunker import MultiLanguageChunker
from chunking.tree_sitter import (
    TreeSitterChunk,
    TreeSitterChunker,
    _collect_error_line_ranges,
    _uncovered_line_ranges,
)
from search.filters import PathFilter


C_FAMILY_EXTS = tuple(
    ext for ext, language in EXT_TO_LANGUAGE.items() if language in ("c", "cpp")
)

# The conditional directives `_neutralize` blanks before parsing: they are
# never chunk content by design, so they are not counted as dropped.
_CONDITIONAL_RE = re.compile(rb"^[ \t]*#[ \t]*(?:if|ifdef|ifndef|elif|else|endif)\b")
_TRIVIA = {b"{", b"}", b"};", b"});"}

_chunker: TreeSitterChunker | None = None
_converter: MultiLanguageChunker | None = None


def _worker_init() -> None:
    logging.disable(logging.CRITICAL)
    global _chunker, _converter
    _converter = MultiLanguageChunker()
    _chunker = _converter.tree_sitter_chunker


def _chunk_id_key(chunk: TreeSitterChunk) -> tuple[Any, ...]:
    """The parts of the chunk id `Embedder._build_chunk_id` builds, minus path.

    Mirrors `MultiLanguageChunker._convert_tree_chunks`: the node type maps
    to a chunk type (many to one) and the name is qualified by its parent.
    """
    assert _converter is not None
    parent = chunk.parent_class or chunk.metadata.get("parent_name")
    name = chunk.metadata.get("name")
    chunk_type = _converter._map_node_type(
        chunk.node_type, parent, chunk.metadata.get("parent_type"), chunk.language
    )
    qualified = f"{parent}.{name}" if parent and name else name
    return (chunk.start_line, chunk.end_line, chunk_type, qualified)


def _comment_rows(root_node: Any, lines: list[bytes]) -> set[int]:
    """0-based rows whose first non-blank byte sits inside a comment node."""
    rows: set[int] = set()
    stack = [root_node]
    while stack:
        node = stack.pop()
        if node.type == "comment":
            (r0, c0), (r1, c1) = node.start_point, node.end_point
            for r in range(r0, min(r1, len(lines) - 1) + 1):
                line = lines[r]
                first = len(line) - len(line.lstrip())
                if r == r0 and first != c0:
                    continue  # trailing comment after code on the same line
                if r == r1 and r > r0 and first >= c1:
                    continue
                rows.add(r)
            continue
        stack.extend(node.children)
    return rows


def _measure_file(job: tuple[str, str]) -> dict[str, Any] | None:
    abs_path, rel_path = job
    assert _chunker is not None
    try:
        parsed = _chunker.parse_file(abs_path, rel_path=rel_path)
        if parsed is None:
            return None
        chunks = _chunker.chunk_parsed(parsed)
    except Exception as e:  # noqa: BLE001 - one bad file must not abort the sweep
        return {"path": rel_path, "failed": str(e)}

    lines = parsed.content.encode("utf-8").split(b"\n")
    root = parsed.tree.root_node
    comment_rows = _comment_rows(root, lines)

    covered: set[int] = set()  # 1-based lines
    for chunk in chunks:
        covered.update(range(chunk.start_line, chunk.end_line + 1))
    for chunk in chunks:
        if not chunk.metadata.get("docstring"):
            continue
        row = chunk.start_line - 2  # 0-based row just above the chunk
        while row >= 0 and row in comment_rows:
            covered.add(row + 1)
            row -= 1

    error_ranges = parsed.error_line_ranges or (
        _collect_error_line_ranges(root) if root.has_error else ()
    )
    error_lines: set[int] = set()
    for start, end in error_ranges:
        error_lines.update(range(start, end + 1))
    error_dropped = 0
    for start, end in _uncovered_line_ranges(error_ranges, chunks):
        error_dropped += sum(
            1 for i in range(start, end + 1) if i <= len(lines) and lines[i - 1].strip()
        )

    root_children = [(c.start_point[0], c.end_point[0], c.type) for c in root.children]
    buckets: Counter[str] = Counter()
    code = directive = comment = 0
    dropped_code = dropped_directive = dropped_comment = 0
    for row, line in enumerate(lines):
        text = line.strip()
        if not text or text in _TRIVIA or _CONDITIONAL_RE.match(line):
            continue
        is_dropped = (row + 1) not in covered
        if row in comment_rows:
            comment += 1
            dropped_comment += is_dropped
        elif text.startswith(b"#"):
            directive += 1
            dropped_directive += is_dropped
        else:
            code += 1
            if is_dropped:
                dropped_code += 1
                kind = next((t for s, e, t in root_children if s <= row <= e), "(none)")
                buckets[kind] += 1

    defs: Counter[str] = Counter()
    for chunk in chunks:
        name = chunk.metadata.get("name")
        if name:
            defs[f"{chunk.node_type}:{name}"] += 1
    # A repeated chunk id fails a full reindex.
    id_keys = {_chunk_id_key(c) for c in chunks}

    return {
        "path": rel_path,
        "lines": len(lines),
        "chunks": len(chunks),
        "code": code,
        "directive": directive,
        "comment": comment,
        "dropped_code": dropped_code,
        "dropped_directive": dropped_directive,
        "dropped_comment": dropped_comment,
        "error_lines": len(error_lines),
        "error_dropped": error_dropped,
        "duplicate_ids": len(chunks) - len(id_keys),
        "buckets": dict(buckets),
        "kinds": dict(Counter(c.node_type for c in chunks)),
        "defs": dict(defs),
    }


def _discover(root: Path, exts: tuple[str, ...], index_filter: bool) -> list[str]:
    path_filter = PathFilter(None, None, root) if index_filter else None
    found: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in filenames:
            if not filename.lower().endswith(exts):
                continue
            rel = Path(dirpath, filename).relative_to(root).as_posix()
            if path_filter is not None and not path_filter.should_index_file(rel):
                continue
            found.append(rel)
    return sorted(found)


_TOTAL_KEYS = (
    "chunks",
    "code",
    "dropped_code",
    "directive",
    "dropped_directive",
    "comment",
    "dropped_comment",
    "error_lines",
    "error_dropped",
    "duplicate_ids",
)


def _totals(records: list[dict[str, Any]]) -> dict[str, Any]:
    # `.get`: baselines taken before `duplicate_ids`/`kinds` existed lack them.
    totals: dict[str, Any] = {k: sum(r.get(k, 0) for r in records) for k in _TOTAL_KEYS}
    buckets: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    for r in records:
        buckets.update(r["buckets"])
        kinds.update(r.get("kinds", {}))
    totals["files"] = len(records)
    totals["definitions"] = sum(sum(r["defs"].values()) for r in records)
    totals["buckets"] = dict(buckets.most_common())
    totals["kinds"] = dict(kinds.most_common())
    return totals


def _print_summary(totals: dict[str, Any], base: dict[str, Any] | None) -> None:
    def delta(key: str) -> str:
        if base is None or key not in base:
            return ""
        d = totals[key] - base[key]
        return f"  ({d:+,})"

    print("=" * 72)
    print(f"{'files':<24}{totals['files']:>12,}{delta('files')}")
    print(f"{'chunks':<24}{totals['chunks']:>12,}{delta('chunks')}")
    print(f"{'definitions':<24}{totals['definitions']:>12,}{delta('definitions')}")
    for key in _TOTAL_KEYS[1:]:
        print(f"{key:<24}{totals[key]:>12,}{delta(key)}")
    print("dropped code lines by enclosing root node:")
    base_buckets = base.get("buckets", {}) if base else {}
    for kind, n in list(totals["buckets"].items())[:10]:
        d = f"  ({n - base_buckets.get(kind, 0):+,})" if base else ""
        print(f"  {kind:<34}{n:>8,}{d}")
    if base:
        for kind in base_buckets:
            if kind not in totals["buckets"]:
                print(f"  {kind:<34}{0:>8,}  ({-base_buckets[kind]:+,})")
    base_kinds = base.get("kinds") if base else None
    print("chunks by node type:")
    for kind in sorted(
        set(totals["kinds"]) | set(base_kinds or ()),
        key=lambda k: -totals["kinds"].get(k, 0),
    ):
        n = totals["kinds"].get(kind, 0)
        d = f"  ({n - base_kinds.get(kind, 0):+,})" if base_kinds is not None else ""
        print(f"  {kind:<34}{n:>8,}{d}")
    print("=" * 72)


def _compare(
    records: list[dict[str, Any]],
    base_records: list[dict[str, Any]],
    failed: list[dict[str, Any]],
) -> None:
    by_path = {r["path"]: r for r in base_records}
    regressed: list[tuple[str, int, int, list[str]]] = []
    improved = 0
    # A baseline holds only files that chunked, so any of them failing now is
    # a regression, not a file to skip.
    newly_failed = [f for f in failed if f["path"] in by_path]
    for r in records:
        b = by_path.get(r["path"])
        if b is None:
            continue
        lost = Counter(b["defs"]) - Counter(r["defs"])
        more_errors = r["error_lines"] - b["error_lines"]
        dups = r["duplicate_ids"]
        if lost or more_errors > 0 or dups:
            regressed.append((r["path"], more_errors, dups, sorted(lost.elements())))
        elif (
            r["dropped_code"] < b["dropped_code"] or r["error_lines"] < b["error_lines"]
        ):
            improved += 1
    print(
        f"improved files: {improved}   "
        f"regressed files: {len(regressed) + len(newly_failed)}"
    )
    for f in newly_failed:
        print(f"  REGRESSED {f['path']}: chunking failed: {f['failed']}")
    for path, more_errors, dups, lost in regressed[:40]:
        shown = ", ".join(lost[:8]) + (
            f" (+{len(lost) - 8} more)" if len(lost) > 8 else ""
        )
        print(
            f"  REGRESSED {path}: error_lines {more_errors:+d}; "
            f"duplicate_ids {dups}; lost [{shown}]"
        )
    if len(regressed) > 40:
        print(f"  ... {len(regressed) - 40} more regressed files")


def main() -> None:
    """Measure whole-file chunk coverage of C-family sources under a root."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("root", help="Directory tree to measure")
    parser.add_argument(
        "--ext",
        default=",".join(C_FAMILY_EXTS),
        help="Comma-separated extensions (default: every C-family extension)",
    )
    parser.add_argument("--top", type=int, default=12, help="Top-N files to list")
    parser.add_argument("--json", help="Write per-file records and totals here")
    parser.add_argument("--compare", help="A previous --json output to diff against")
    parser.add_argument(
        "--index-filter",
        action="store_true",
        help="Skip files the default PathFilter would not index",
    )
    parser.add_argument(
        "--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2)
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    exts = tuple(e.strip().lower() for e in args.ext.split(",") if e.strip())
    files = _discover(root, exts, args.index_filter)
    print(f"Root: {root}")
    print(
        f"Files: {len(files)}  (index filter: {'on' if args.index_filter else 'off'})"
    )

    jobs = [(str(root / rel), rel) for rel in files]
    with ProcessPoolExecutor(
        max_workers=args.workers, initializer=_worker_init
    ) as pool:
        results = list(pool.map(_measure_file, jobs, chunksize=8))
    failed = [r for r in results if r is not None and "failed" in r]
    records = [r for r in results if r is not None and "failed" not in r]
    if failed:
        print(
            f"chunking failed for {len(failed)} file(s): {[f['path'] for f in failed[:5]]}"
        )

    totals = _totals(records)
    base_doc = None
    if args.compare:
        base_doc = json.loads(Path(args.compare).read_text(encoding="utf-8"))
        if base_doc.get("index_filter") != args.index_filter:
            print("NOTE: baseline was taken with a different --index-filter setting")
    _print_summary(totals, base_doc["totals"] if base_doc else None)

    print(f"top {args.top} files by dropped code lines:")
    for r in sorted(records, key=lambda r: r["dropped_code"], reverse=True)[: args.top]:
        print(
            f"  {r['dropped_code']:>6,}  err {r['error_dropped']:>5,}  "
            f"cmt {r['dropped_comment']:>5,}  {r['path']}"
        )

    if base_doc:
        _compare(records, base_doc["files"], failed)

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(
                {
                    "root": str(root),
                    "index_filter": args.index_filter,
                    "totals": totals,
                    "files": records,
                },
                indent=1,
            ),
            encoding="utf-8",
        )
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
