#!/usr/bin/env python
"""Corpus analysis for chunking-parameter derivation (analysis-only).

Measures the repository's actual code-size statistics and compares them
against the live ``search_config.json`` chunking parameters, following the
methodology in ``_archive/IMPROVEMENTS/JULY_IMPROVEMENTS/Adaptive_chncking_strategies.md``:

1. Per-language function/class/file size distributions (lines, non-whitespace
   chars, whitespace tokens, real embedder-BPE tokens).
2. Token-estimation calibration (real tokens vs whitespace words).
3. Produced-chunk audit: run the live chunking pipeline in-process and measure
   the chunk-size distribution it actually emits (headline: chunks < 150 real
   tokens, since the live config runs merge-free).
4. Dormant-merge simulation: what ``_greedy_merge_small_chunks`` /
   ``remerge_chunks_with_communities`` would produce with live and derived
   parameters.
5. Call-graph stats + Louvain gamma sweep (resolution x seed) on the stored
   collapsed graph, for the ``community_resolution`` recommendation.
6. Duplication ratio (k=8 token shingles) and comment/docstring density.
7. Derived parameter recommendations (reported, never applied).

Read-only with respect to the index: loads the stored call graph and community
map, never writes to storage. Does not modify any config.

Usage:
    .venv/Scripts/python.exe scripts/benchmark/analyze_chunking_corpus.py \
        --project . --json evaluation/chunking_corpus_stats.json
"""

from __future__ import annotations

import argparse
import ast as pyast
import json
import logging
import math
import os
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("corpus_analysis")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stderr)
_handler.setFormatter(logging.Formatter("[ANALYZE] %(message)s"))
logger.addHandler(_handler)
logger.propagate = False


# ---------------------------------------------------------------------------
# Small statistics helpers (no numpy dependency needed)
# ---------------------------------------------------------------------------


def percentile(sorted_vals: list[float], q: float) -> float:
    """Linear-interpolation percentile on a pre-sorted list (q in [0, 1])."""
    if not sorted_vals:
        return 0.0
    idx = (len(sorted_vals) - 1) * q
    lo, hi = math.floor(idx), math.ceil(idx)
    if lo == hi:
        return float(sorted_vals[lo])
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (idx - lo)


def dist(values: Sequence[float]) -> dict:
    """Summary distribution: count, mean, p10..p90, max."""
    if not values:
        return {"count": 0}
    sv = sorted(values)
    return {
        "count": len(sv),
        "mean": round(sum(sv) / len(sv), 1),
        "p10": round(percentile(sv, 0.10), 1),
        "p25": round(percentile(sv, 0.25), 1),
        "p50": round(percentile(sv, 0.50), 1),
        "p75": round(percentile(sv, 0.75), 1),
        "p90": round(percentile(sv, 0.90), 1),
        "max": round(float(sv[-1]), 1),
    }


def adjusted_rand_index(labels_a: list[int], labels_b: list[int]) -> float:
    """ARI via pair counting (sklearn-free)."""
    from math import comb

    n = len(labels_a)
    if n < 2:
        return 1.0
    pair_counts: Counter = Counter(zip(labels_a, labels_b, strict=True))
    a_counts: Counter = Counter(labels_a)
    b_counts: Counter = Counter(labels_b)
    sum_pairs = sum(comb(v, 2) for v in pair_counts.values())
    sum_a = sum(comb(v, 2) for v in a_counts.values())
    sum_b = sum(comb(v, 2) for v in b_counts.values())
    total = comb(n, 2)
    expected = sum_a * sum_b / total if total else 0.0
    max_index = (sum_a + sum_b) / 2
    denom = max_index - expected
    if denom == 0:
        return 1.0
    return (sum_pairs - expected) / denom


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Real-token counting (embedder BPE)
# ---------------------------------------------------------------------------


class TokenCounter:
    """Counts real BPE tokens with the live embedder's tokenizer.

    Falls back to tiktoken cl100k_base if the HF tokenizer is unavailable;
    the ``backend`` attribute records which one was used.
    """

    def __init__(self, model_name: str) -> None:
        self.backend = "none"
        self._hf = None
        self._tk = None
        try:
            from transformers import AutoTokenizer

            try:
                self._hf = AutoTokenizer.from_pretrained(
                    model_name, local_files_only=True
                )
            except OSError:
                self._hf = AutoTokenizer.from_pretrained(model_name)
            self.backend = f"hf:{model_name}"
        except Exception as e:  # noqa: BLE001 - fall back to tiktoken; analysis script must degrade, not die
            logger.info(f"HF tokenizer unavailable ({e}); falling back to tiktoken")
            import tiktoken

            self._tk = tiktoken.get_encoding("cl100k_base")
            self.backend = "tiktoken:cl100k_base"

    def count_many(self, texts: list[str], batch_size: int = 64) -> list[int]:
        counts: list[int] = []
        if self._hf is not None:
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                encoded = self._hf(batch, add_special_tokens=False)["input_ids"]
                counts.extend(len(ids) for ids in encoded)
        else:
            assert self._tk is not None  # constructor guarantees one backend
            counts.extend(len(self._tk.encode(t)) for t in texts)
        return counts

    def count(self, text: str) -> int:
        return self.count_many([text])[0]


# ---------------------------------------------------------------------------
# Pass 0: file discovery (replicates MultiLanguageChunker.chunk_directory walk)
# ---------------------------------------------------------------------------


def discover_files(project_root: Path, extra_excluded: set[str]) -> list[str]:
    from chunking.language_registry import DEFAULT_IGNORED_DIRS, SUPPORTED_EXTENSIONS

    ignored = set(DEFAULT_IGNORED_DIRS) | extra_excluded
    rel_files: set[str] = set()
    for ext in SUPPORTED_EXTENSIONS:
        for file_path in project_root.rglob(f"*{ext}"):
            try:
                rel_parts = file_path.relative_to(project_root).parts
            except ValueError:
                continue
            if any(part in ignored for part in rel_parts):
                continue
            rel_files.add(str(file_path.relative_to(project_root)))
    return sorted(rel_files)


def load_index_exclusions(storage_dir: Path | None) -> set[str]:
    """Read the live index's directory exclusions from project_info.json so the
    analyzed corpus matches what the index actually serves."""
    if storage_dir is None:
        return set()
    info_path = storage_dir / "project_info.json"
    if not info_path.exists():
        return set()
    info = json.loads(info_path.read_text(encoding="utf-8"))
    excluded = set(info.get("default_excluded_dirs") or [])
    excluded |= set(info.get("user_excluded_dirs") or [])
    return excluded


# ---------------------------------------------------------------------------
# Pass 1: AST-level statistics (functions, classes, files, comment density)
# ---------------------------------------------------------------------------


def collect_ast_stats(
    project_root: Path, rel_files: list[str], counter: TokenCounter
) -> dict:
    """Per-language function/class/file size stats via the profiler's own seam."""
    from chunking.languages.base import LanguageChunker, estimate_characters
    from chunking.tree_sitter import TreeSitterChunker

    dispatcher = TreeSitterChunker()
    class_types = LanguageChunker._CLASS_LEVEL_NODE_TYPES

    functions: list[dict] = []  # lang, name, rel_path, lines, nw, ws, cc
    classes: list[dict] = []
    files: list[dict] = []
    comment_nw_by_lang: Counter = Counter()
    docstring_nw_by_lang: Counter = Counter()
    total_nw_by_lang: Counter = Counter()
    file_token_lists: dict[str, list[str]] = {}  # rel_path -> ws tokens (for shingles)
    parse_failures: list[str] = []

    def count_comment_nw(node, source_bytes: bytes) -> int:
        if node.type == "comment":
            text = source_bytes[node.start_byte : node.end_byte].decode(
                "utf-8", errors="ignore"
            )
            return estimate_characters(text, count_whitespace=False)
        return sum(count_comment_nw(child, source_bytes) for child in node.children)

    def process_file(parsed, rel_path: str) -> None:
        content = parsed.content
        chunker = parsed.chunker
        language = getattr(chunker, "language_name", None) or type(chunker).__name__
        source_bytes = content.encode("utf-8")
        function_node_types = getattr(chunker, "function_node_types", frozenset())

        file_nw = estimate_characters(content, count_whitespace=False)
        file_ws_tokens = content.split()
        files.append(
            {
                "rel_path": rel_path,
                "lang": language,
                "lines": content.count("\n") + 1,
                "nw": file_nw,
                "ws": len(file_ws_tokens),
            }
        )
        file_token_lists[rel_path] = file_ws_tokens
        total_nw_by_lang[language] += file_nw

        # Comment density: sum nw-chars of tree-sitter `comment` nodes.
        comment_nw_by_lang[language] += count_comment_nw(
            parsed.tree.root_node, source_bytes
        )

        # Python docstrings via the stdlib ast (tree-sitter has no docstring type).
        if language == "python":
            try:
                module = pyast.parse(content)
                for node in pyast.walk(module):
                    if isinstance(
                        node,
                        (
                            pyast.Module,
                            pyast.ClassDef,
                            pyast.FunctionDef,
                            pyast.AsyncFunctionDef,
                        ),
                    ):
                        doc = pyast.get_docstring(node)
                        if doc:
                            docstring_nw_by_lang[language] += estimate_characters(
                                doc, count_whitespace=False
                            )
            except SyntaxError:
                pass

        # Function/class traversal mirrors chunking/repo_profiler.py:profile_parsed
        # (top-level functions + methods only, no nested double-count).
        def traverse(node, inside_function: bool = False) -> None:
            node_type = node.type
            if node_type in function_node_types and not inside_function:
                text = source_bytes[node.start_byte : node.end_byte].decode(
                    "utf-8", errors="ignore"
                )
                try:
                    cc = chunker.get_node_complexity(node)
                except Exception:  # noqa: BLE001 - complexity is best-effort metadata
                    cc = 1
                functions.append(
                    {
                        "lang": language,
                        "rel_path": rel_path,
                        "lines": node.end_point[0] - node.start_point[0] + 1,
                        "nw": estimate_characters(text, count_whitespace=False),
                        "ws": len(text.split()),
                        "cc": cc,
                        "text": text,
                    }
                )
                for child in node.children:
                    traverse(child, inside_function=True)
                return
            if node_type in class_types and not inside_function:
                text = source_bytes[node.start_byte : node.end_byte].decode(
                    "utf-8", errors="ignore"
                )
                classes.append(
                    {
                        "lang": language,
                        "rel_path": rel_path,
                        "lines": node.end_point[0] - node.start_point[0] + 1,
                        "nw": estimate_characters(text, count_whitespace=False),
                        "ws": len(text.split()),
                        "text": text,
                    }
                )
                for child in node.children:
                    traverse(child, inside_function=False)
                return
            if not inside_function:
                for child in node.children:
                    traverse(child, inside_function=False)

        traverse(parsed.tree.root_node)

    for rel_path in rel_files:
        abs_path = project_root / rel_path
        try:
            parsed = dispatcher.parse_file(
                str(abs_path), rel_path=rel_path, emit_parse_warnings=False
            )
        except Exception as e:  # noqa: BLE001 - parse-recovery: mirror profiler behaviour, skip unparseable files
            parse_failures.append(f"{rel_path}: {e}")
            continue
        if parsed is None or not parsed.content.strip():
            continue
        process_file(parsed, rel_path)

    # Real-token counts, batched.
    logger.info(
        f"Tokenizing {len(functions)} functions + {len(classes)} classes "
        f"with {counter.backend}"
    )
    func_tokens = counter.count_many([f["text"] for f in functions])
    class_tokens = counter.count_many([c["text"] for c in classes])
    for f, t in zip(functions, func_tokens, strict=True):
        f["real"] = t
        del f["text"]
    for c, t in zip(classes, class_tokens, strict=True):
        c["real"] = t
        del c["text"]

    return {
        "functions": functions,
        "classes": classes,
        "files": files,
        "comment_nw_by_lang": dict(comment_nw_by_lang),
        "docstring_nw_by_lang": dict(docstring_nw_by_lang),
        "total_nw_by_lang": dict(total_nw_by_lang),
        "file_token_lists": file_token_lists,
        "parse_failures": parse_failures,
    }


# ---------------------------------------------------------------------------
# Pass 2: produced-chunk audit (run the live pipeline in-process)
# ---------------------------------------------------------------------------


def audit_produced_chunks(
    project_root: Path, rel_files: list[str], counter: TokenCounter
) -> tuple[list[dict], list, object]:
    """Chunk the corpus with the live config + adaptive profile; measure output.

    Mirrors the full-index flow in search/incremental_indexer.py: build the
    RepoProfile first (sizing_mode="adaptive" live), attach it to the
    tree-sitter chunker, then chunk every file.
    """
    from chunking.multi_language_chunker import MultiLanguageChunker
    from chunking.repo_profiler import profile_repository

    repo_profile = profile_repository(str(project_root), rel_files)
    logger.info(f"RepoProfile: {repo_profile}")

    chunker = MultiLanguageChunker(root_path=str(project_root))
    chunker.tree_sitter_chunker.repo_profile = repo_profile

    all_chunks = []
    for rel_path in rel_files:
        all_chunks.extend(chunker.chunk_file(str(project_root / rel_path)))

    from chunking.languages.base import estimate_characters

    real_counts = counter.count_many([c.content for c in all_chunks])
    records = [
        {
            "chunk_id": c.chunk_id,
            "type": c.chunk_type,
            "lang": c.language,
            "lines": c.end_line - c.start_line + 1,
            "nw": estimate_characters(c.content, count_whitespace=False),
            "ws": len(c.content.split()),
            "real": real,
        }
        for c, real in zip(all_chunks, real_counts, strict=True)
    ]
    return records, all_chunks, repo_profile


# ---------------------------------------------------------------------------
# Pass 4: call-graph stats + gamma sweep
# ---------------------------------------------------------------------------


def locate_graph_storage(project_root: Path, model_name: str) -> Path | None:
    storage_root = Path(
        os.environ.get("CODE_SEARCH_STORAGE", Path.home() / ".claude_code_search")
    )
    projects_dir = storage_root / "projects"
    if not projects_dir.exists():
        return None
    slug = model_name.split("/")[-1].lower()
    candidates = sorted(
        d
        for d in projects_dir.iterdir()
        if d.is_dir() and d.name.startswith(f"{project_root.name}_") and slug in d.name
    )
    return candidates[-1] if candidates else None


def collapse_graph(nx_graph, max_phantom_degree: int):
    """Replicates CommunityDetector.detect_communities preprocessing exactly
    (graph/community_detector.py) so the sweep runs on the same collapsed graph
    production Louvain sees. Kept separate because the detector hardcodes
    seed=42 and cannot vary seeds."""
    import networkx as nx

    from graph.schema import (
        NODE_ATTR_IS_TARGET_NAME,
        NODE_ATTR_TYPE,
        NODE_TYPE_SYMBOL_NAME,
    )

    chunk_nodes = [
        n
        for n, attrs in nx_graph.nodes(data=True)
        if attrs.get(NODE_ATTR_TYPE) != NODE_TYPE_SYMBOL_NAME
        and not attrs.get(NODE_ATTR_IS_TARGET_NAME, False)
    ]
    phantom_nodes = [
        n
        for n, attrs in nx_graph.nodes(data=True)
        if attrs.get(NODE_ATTR_TYPE) == NODE_TYPE_SYMBOL_NAME
        or attrs.get(NODE_ATTR_IS_TARGET_NAME, False)
    ]
    collapsed = nx.Graph()
    chunk_set = set(chunk_nodes)
    for node in chunk_nodes:
        collapsed.add_node(node)
    direct_edges = 0
    for u, v in nx_graph.edges():
        if u in chunk_set and v in chunk_set and u != v:
            if collapsed.has_edge(u, v):
                collapsed[u][v]["weight"] += 1
            else:
                collapsed.add_edge(u, v, weight=1)
                direct_edges += 1
    collapsed_edges = 0
    skipped_phantoms = 0
    for phantom in phantom_nodes:
        callers = [p for p in nx_graph.predecessors(phantom) if p in chunk_set]
        if len(callers) > max_phantom_degree:
            skipped_phantoms += 1
            continue
        if len(callers) > 1:
            for i, c1 in enumerate(callers):
                for c2 in callers[i + 1 :]:
                    if collapsed.has_edge(c1, c2):
                        collapsed[c1][c2]["weight"] += 1
                    else:
                        collapsed.add_edge(c1, c2, weight=1)
                        collapsed_edges += 1
    meta = {
        "chunk_nodes": len(chunk_nodes),
        "phantom_nodes": len(phantom_nodes),
        "skipped_phantoms_over_degree": skipped_phantoms,
        "direct_chunk_chunk_edges": direct_edges,
        "phantom_coreference_edges": collapsed_edges,
    }
    return collapsed, meta


def gamma_sweep(collapsed, gammas: list[float], seeds: list[int]) -> list[dict]:
    from networkx.algorithms.community import louvain_communities, modularity

    node_order = sorted(collapsed.nodes())
    rows = []
    for gamma in gammas:
        q_scores, counts, partitions = [], [], []
        for seed in seeds:
            comms = louvain_communities(collapsed, resolution=gamma, seed=seed)
            counts.append(len(comms))
            if collapsed.number_of_edges() > 0:
                q_scores.append(modularity(collapsed, comms, resolution=gamma))
            label_of = {}
            for cid, nodes in enumerate(comms):
                for n in nodes:
                    label_of[n] = cid
            partitions.append([label_of[n] for n in node_order])
        aris = [
            adjusted_rand_index(partitions[i], partitions[j])
            for i in range(len(partitions))
            for j in range(i + 1, len(partitions))
        ]
        rows.append(
            {
                "gamma": gamma,
                "mean_q": round(sum(q_scores) / len(q_scores), 4) if q_scores else None,
                "mean_communities": round(sum(counts) / len(counts), 1),
                "min_communities": min(counts),
                "max_communities": max(counts),
                "mean_pairwise_ari": round(sum(aris) / len(aris), 4) if aris else 1.0,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Pass 5: duplication ratio (k=8 whitespace-token shingles)
# ---------------------------------------------------------------------------


def duplication_stats(file_token_lists: dict[str, list[str]], k: int = 8) -> dict:
    total = 0
    seen: set[int] = set()
    dup = 0
    file_shingles: dict[str, set[int]] = {}
    for rel_path, tokens in file_token_lists.items():
        shingles = set()
        for i in range(len(tokens) - k + 1):
            h = hash(tuple(tokens[i : i + k]))
            shingles.add(h)
            total += 1
            if h in seen:
                dup += 1
            else:
                seen.add(h)
        file_shingles[rel_path] = shingles
    near_dup_pairs = []
    paths = sorted(file_shingles)
    for i, p1 in enumerate(paths):
        s1 = file_shingles[p1]
        if not s1:
            continue
        for p2 in paths[i + 1 :]:
            s2 = file_shingles[p2]
            if not s2:
                continue
            inter = len(s1 & s2)
            if inter == 0:
                continue
            jac = inter / (len(s1) + len(s2) - inter)
            if jac >= 0.5:
                near_dup_pairs.append({"a": p1, "b": p2, "jaccard": round(jac, 3)})
    return {
        "shingle_k": k,
        "total_shingles": total,
        "unique_shingles": len(seen),
        "duplication_ratio": round(dup / total, 4) if total else 0.0,
        "near_duplicate_file_pairs_j50": sorted(
            near_dup_pairs, key=lambda d: -d["jaccard"]
        )[:20],
    }


# ---------------------------------------------------------------------------
# Derivations (research-doc formulas; reported, never applied)
# ---------------------------------------------------------------------------


def derive_recommendations(
    py_funcs: list[dict],
    gamma_rows: list[dict],
    calibration: dict,
    repo_profile,
) -> dict:
    real = sorted(f["real"] for f in py_funcs)
    lines = sorted(f["lines"] for f in py_funcs)
    nw = sorted(f["nw"] for f in py_funcs)
    p90_real = percentile(real, 0.90)
    p90_lines = percentile(lines, 0.90)
    p90_nw = percentile(nw, 0.90)
    p50_real = percentile(real, 0.50)
    p10_real = percentile(real, 0.10)

    best_gamma = None
    if gamma_rows:
        best_gamma = max(
            gamma_rows,
            key=lambda r: (round(r["mean_pairwise_ari"], 2), r["mean_q"] or 0),
        )["gamma"]

    return {
        "max_merged_tokens_rec": int(clamp(p90_real * 1.2, 400, 1000)),
        "max_merged_tokens_formula": "clamp(p90_func_real_tokens * 1.2, 400, 1000)",
        "p90_func_real_tokens": round(p90_real, 1),
        "max_chunk_lines_rec": int(clamp(p90_lines * 1.25, 60, 150)),
        "max_chunk_lines_formula": "clamp(p90_func_lines * 1.25, 60, 150)",
        "p90_func_lines": round(p90_lines, 1),
        "max_split_chars_note": (
            f"p90 function nw-chars = {p90_nw:.0f}; cAST optimum band 2000-2500 "
            f"nw-chars; live value 3000"
        ),
        "min_chunk_tokens_vs_p10_real": round(p10_real, 1),
        "dispersion_p90_over_p50_real": round(p90_real / p50_real, 2)
        if p50_real
        else None,
        "community_resolution_rec": best_gamma,
        "whitespace_correction_factor": calibration,
        "repo_profile_live": {
            "function_count": repo_profile.function_count,
            "p25_chars": repo_profile.p25_chars,
            "p50_chars": repo_profile.p50_chars,
            "p75_chars": repo_profile.p75_chars,
            "p90_chars": repo_profile.p90_chars,
            "max_complexity": repo_profile.max_complexity,
        }
        if repo_profile
        else None,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".", help="Project root to analyze")
    parser.add_argument(
        "--json", dest="json_out", default=None, help="JSON output path"
    )
    parser.add_argument(
        "--skip-gamma-sweep", action="store_true", help="Skip the Louvain sweep"
    )
    args = parser.parse_args()

    project_root = Path(args.project).resolve()
    logger.info(f"Project: {project_root}")

    from search.config import get_search_config

    config = get_search_config()
    chunking_cfg = config.chunking
    model_name = config.embedding.model_name
    live_chunking = {
        k: getattr(chunking_cfg, k)
        for k in (
            "enable_large_node_splitting",
            "max_chunk_lines",
            "split_size_method",
            "max_split_chars",
            "sizing_mode",
            "adaptive_multiplier_max",
            "adaptive_multiplier_min",
            "max_complexity_cap",
        )
    }
    logger.info(f"Live chunking config: {live_chunking}")

    counter = TokenCounter(model_name)

    # Pass 0 + 1 — corpus scoped to the live index's exclusions when available
    storage_dir = locate_graph_storage(project_root, model_name)
    extra_excluded = load_index_exclusions(storage_dir)
    if extra_excluded:
        logger.info(
            f"Applying live-index exclusions from project_info.json "
            f"({len(extra_excluded)} dirs)"
        )
    rel_files = discover_files(project_root, extra_excluded)
    logger.info(f"Discovered {len(rel_files)} supported files")
    ast_stats = collect_ast_stats(project_root, rel_files, counter)
    functions = ast_stats["functions"]
    classes = ast_stats["classes"]
    files = ast_stats["files"]

    by_lang: dict[str, list[dict]] = defaultdict(list)
    for f in functions:
        by_lang[f["lang"]].append(f)

    func_stats = {}
    calibration = {}
    for lang, funcs in sorted(by_lang.items()):
        func_stats[lang] = {
            "lines": dist([f["lines"] for f in funcs]),
            "nw_chars": dist([f["nw"] for f in funcs]),
            "ws_tokens": dist([f["ws"] for f in funcs]),
            "real_tokens": dist([f["real"] for f in funcs]),
            "complexity": dist([f["cc"] for f in funcs]),
        }
        total_ws = sum(f["ws"] for f in funcs)
        total_real = sum(f["real"] for f in funcs)
        total_nw = sum(f["nw"] for f in funcs)
        calibration[lang] = {
            "real_per_ws_token": round(total_real / total_ws, 3) if total_ws else None,
            "nw_chars_per_real_token": round(total_nw / total_real, 3)
            if total_real
            else None,
            "function_count": len(funcs),
        }

    density = {}
    for lang, total_nw in ast_stats["total_nw_by_lang"].items():
        c = ast_stats["comment_nw_by_lang"].get(lang, 0)
        d = ast_stats["docstring_nw_by_lang"].get(lang, 0)
        density[lang] = {
            "comment_nw_ratio": round(c / total_nw, 4) if total_nw else 0,
            "docstring_nw_ratio": round(d / total_nw, 4) if total_nw else 0,
        }

    # Pass 2: produced chunks
    chunk_records, code_chunks, repo_profile = audit_produced_chunks(
        project_root, rel_files, counter
    )
    reals = [r["real"] for r in chunk_records]
    by_type: dict[str, list[int]] = defaultdict(list)
    for r in chunk_records:
        by_type[r["type"]].append(r["real"])
    produced = {
        "total_chunks": len(chunk_records),
        "chunk_type_counts": dict(
            Counter(r["type"] for r in chunk_records).most_common()
        ),
        "real_tokens_all": dist(reals),
        "under_150_real": sum(1 for r in reals if r < 150),
        "under_50_real": sum(1 for r in reals if r < 50),
        "over_800_real": sum(1 for r in reals if r > 800),
        "over_2048_real": sum(1 for r in reals if r > 2048),
        "real_tokens_by_type": {t: dist(v) for t, v in sorted(by_type.items())},
        "under_150_by_type": {
            t: sum(1 for x in v if x < 150) for t, v in sorted(by_type.items())
        },
    }

    # Graph + community map
    graph_result = None
    gamma_rows = []
    community_map = None
    if storage_dir is not None:
        from graph.graph_storage import CodeGraphStorage

        graph_files = list(storage_dir.glob("*_call_graph.json"))
        if graph_files:
            project_id = graph_files[0].name[: -len("_call_graph.json")]
            storage = CodeGraphStorage(project_id, storage_dir=storage_dir)
            if storage.load():
                # Community detection/storage was removed from the codebase
                # (`35d2f4f` cull + a later graph_storage.py refactor —
                # `CodeGraphStorage.load_community_map` no longer exists).
                # community_map stays None; the `if community_map:` branches
                # below degrade to their documented empty state (0 stored
                # communities, no budget block) rather than crashing.
                # max_phantom_degree was a ChunkingConfig field (default 20)
                # before the community-detection field cull (`35d2f4f`); it is
                # no longer live-tunable, so this analysis-only pass keeps the
                # old default as a literal.
                collapsed, collapse_meta = collapse_graph(storage.graph, 20)
                import networkx as nx

                graph_result = {
                    "storage_dir": str(storage_dir),
                    "nodes": storage.graph.number_of_nodes(),
                    "edges": storage.graph.number_of_edges(),
                    **collapse_meta,
                    "collapsed_nodes": collapsed.number_of_nodes(),
                    "collapsed_edges": collapsed.number_of_edges(),
                    "collapsed_density": round(nx.density(collapsed), 5),
                    "avg_clustering": round(nx.average_clustering(collapsed), 4),
                    "connected_components": nx.number_connected_components(collapsed),
                    "stored_communities": len(set(community_map.values()))
                    if community_map
                    else 0,
                }
                if not args.skip_gamma_sweep:
                    logger.info("Running Louvain gamma sweep (7 gammas x 5 seeds)")
                    gamma_rows = gamma_sweep(
                        collapsed,
                        gammas=[0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0],
                        seeds=[1, 7, 13, 42, 99],
                    )
    else:
        logger.info(
            "No stored index found for this project/model — skipping graph pass"
        )

    # Community token sums (do stored communities fit the merge budget?)
    community_budget = None
    if community_map:
        real_by_id = {r["chunk_id"]: r["real"] for r in chunk_records}
        sums: Counter = Counter()
        matched_chunks = 0
        for chunk_id, real in real_by_id.items():
            cid = community_map.get(chunk_id)
            if cid is not None:
                sums[cid] += real
                matched_chunks += 1
        community_budget = {
            "chunks_matched_to_stored_map": matched_chunks,
            "chunks_total": len(real_by_id),
            "communities_with_matched_chunks": len(sums),
            "community_real_token_sums": dist(list(sums.values())),
            "communities_fitting_1000_real": sum(1 for v in sums.values() if v <= 1000),
            "communities_fitting_400_real": sum(1 for v in sums.values() if v <= 400),
        }

    # Pass 5: duplication
    dup = duplication_stats(ast_stats["file_token_lists"])

    # Derivations (Python functions dominate this corpus)
    py_funcs = by_lang.get("python", [])
    derived = derive_recommendations(py_funcs, gamma_rows, calibration, repo_profile)

    result = {
        "meta": {
            "project": str(project_root),
            "files_analyzed": len(rel_files),
            "tokenizer_backend": counter.backend,
            "parse_failures": ast_stats["parse_failures"],
        },
        "live_chunking_config": live_chunking,
        "function_stats_by_lang": func_stats,
        "class_stats": {
            "lines": dist([c["lines"] for c in classes]),
            "nw_chars": dist([c["nw"] for c in classes]),
            "real_tokens": dist([c["real"] for c in classes]),
        },
        "file_stats": {
            "lines": dist([f["lines"] for f in files]),
            "nw_chars": dist([f["nw"] for f in files]),
            "ws_tokens": dist([f["ws"] for f in files]),
            "lang_file_counts": dict(Counter(f["lang"] for f in files).most_common()),
        },
        "token_calibration": calibration,
        "comment_docstring_density": density,
        "produced_chunks": produced,
        "graph": graph_result,
        "gamma_sweep": gamma_rows,
        "community_token_budget": community_budget,
        "duplication": dup,
        "derived_recommendations": derived,
    }

    output = json.dumps(result, indent=2)
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        logger.info(f"Wrote {out_path}")
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
