#!/usr/bin/env python3
"""Duplicate-tree crowding probe — read-only, pre-registered gate.

Measures whether SDTD's near-identical cross-tree source copies (``Scripts/``,
``StreamDiffusionTD-fork/``, ``StreamDiffusion/StreamDiffusionTD/``) crowd the
30-slot rerank *window*, where damage would be invisible in the previously
recorded top-7 display tables (5/210 = 2.4% waste, 3/6 categories affected).

See the plan (``C:\\Users\\Inter\\.claude\\plans\\stateless-stirring-catmull.md``)
for full context. Summary of what this script does:

1. Reconstructs Arm A (``reranker.enabled=True``, ``top_k_candidates=30``,
   deployed defaults elsewhere) **in memory** via ``evaluation.arm_overrides`` —
   never touches ``search_config.json``, which is currently left in an
   ablated Arm-B state.
2. Installs an ``Instrumentation`` shim (adapted from ``probe_rerank_window.py``)
   that captures every ``_run_rerank`` pass (Pass 1 hop-level, Pass 2
   multi-hop merge, Pass 3 ego-graph tail) and the pre-fusion BM25/dense leg
   lists, without changing any production code path.
3. Runs the 30 pre-registered cross-system queries
   (``evaluation/CROSS_SYSTEM_QUERIES_20260817.md``) against a live,
   already-indexed SDTD project, and for each pass computes:
   window duplicate occupancy (content-hash exact match on normalized
   ``bm25_text``), backfill availability, a dedup-aware-walk recoverability
   count, and (Pass 1 only) a fusion-depth-widened "refused" variant.
4. Re-runs the real cross-encoder on the dedup-aware window to measure
   display-level conversion (P3), and prints every B-category collapsed
   pair for operator inspection (P4 canary).
5. Applies the pre-registered gate (G0 self-validity, P1-P4) and exits with
   the corresponding code — no production code is touched by this script
   regardless of outcome.

Exit codes: 0 pass, 1 ABORT, 2 setup error, 3 HALT.

Usage:
    ./scripts/test/run_tests.sh  # not applicable — this is not a pytest module
    .venv/Scripts/python.exe scripts/benchmark/probe_duplicate_crowding.py \\
        --project-path "D:\\dev\\SDTD_040_Beta" --leg-multiplier both \\
        --json-out evaluation/DUPLICATE_CROWDING_PROBE_20260817.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import median
from typing import Any


def _ensure_pinned_hash_seed() -> None:
    """Re-exec with PYTHONHASHSEED=0 when unset (script execution only).

    Reproducibility: chunk-ID set iteration order feeds candidate-pool
    composition, so unpinned hash randomization flips query results between
    otherwise-identical rounds (ADR-0021). Any explicit PYTHONHASHSEED,
    including "random", is respected. Must only run under __main__ — at
    import time (tests import this module) sys.argv belongs to the importer
    and re-exec'ing it is wrong.
    """
    if os.environ.get("PYTHONHASHSEED") is None:
        print(
            "[HASHSEED] PYTHONHASHSEED unset - re-exec with PYTHONHASHSEED=0 "
            "for reproducible rounds",
            file=sys.stderr,
        )
        raise SystemExit(
            subprocess.call(
                [sys.executable, *sys.argv],
                env={**os.environ, "PYTHONHASHSEED": "0"},
            )
        )


# Add project root to sys.path so imports resolve from any working directory
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# _run_rerank's log_prefix values (reranking_engine.py). Pass 2 (multi-hop
# merge) and Pass 3 (ego-graph/parent-expansion tail) both dispatch under the
# identical MERGE_LOG_PREFIX from RerankingEngine.rerank_by_query -- only the
# nested-call ordinal (see Instrumentation) tells them apart. Pass 1 (the
# hop-level apply_neural_reranking call inside execute_single_hop) uses a
# distinct prefix and is never nested inside a rerank_by_query call.
MERGE_LOG_PREFIX = "[NEURAL_RERANK]"
PASS1_LOG_PREFIX = "[NEURAL_RERANK-SEARCH]"

MIN_NORM_CHARS_DEFAULT = 40
MIN_NORM_CHARS_SENSITIVITY = (0, 40, 120)
SHINGLE_K = 8
JACCARD_THRESHOLDS = (0.8, 0.9)

# Pre-registered gate thresholds (denominator 30 queries x 30 Pass-2 slots = 900)
GATE_P1_MIN_SLOTS = 90
GATE_P1_MIN_MEDIAN = 2
GATE_P2_MIN_ADMITTED = 60
GATE_P2_MIN_NEW_FILES = 30
GATE_P3_MIN_QUERIES_CHANGED = 9
GATE_P3_MIN_NEW_CHUNKS = 15
G0_MIN_CONTENT_COV = 0.95

B_CATEGORY_PREFIXES = ("B1", "B2", "B3", "B4", "B5", "B6")

# The 30 pre-registered cross-system queries, frozen in
# evaluation/CROSS_SYSTEM_QUERIES_20260817.md before any competitor system was
# run. Query text only -- the "known candidate" breadcrumb column is not
# needed for pool-composition measurement.
QUERIES: list[dict[str, str]] = [
    {
        "id": "A1",
        "query": "Where is a CUDA out-of-memory error detected and classified, including OOM errors that surface as generic RuntimeErrors from third-party code like TensorRT?",
    },
    {
        "id": "A2",
        "query": "Where does FP8 calibration retry encoding one image at a time after a batch encode fails, so one bad image doesn't zero out the whole calibration set?",
    },
    {
        "id": "A3",
        "query": "Where is the feedback-loop blend formula between the current input image and the previous frame's diffusion output implemented?",
    },
    {
        "id": "A4",
        "query": "Where does the IPAdapter embedding preprocessor avoid re-encoding a style image through CLIP when it hasn't changed across frames?",
    },
    {
        "id": "A5",
        "query": "Where is a calibration image set's signature hashed to build a cache-key suffix for a TensorRT engine build?",
    },
    {
        "id": "A6",
        "query": "Where is an authentication token stored using OS-native secure storage (DPAPI on Windows, Keychain on macOS)?",
    },
    {
        "id": "A7",
        "query": "Where is the TouchDesigner Script TOP pixel-format string computed from a tensor's dtype and channel count for CUDA memory copy?",
    },
    {
        "id": "A8",
        "query": "Where does a REST endpoint accept an uploaded ControlNet YAML configuration file and parse it?",
    },
    {
        "id": "A9",
        "query": "Where are FP8 calibration prompts loaded from a bundled text file?",
    },
    {
        "id": "A10",
        "query": "Where is TF32 matmul and cuDNN benchmark mode enabled once per CUDA device when the pipeline is constructed?",
    },
    {
        "id": "B1",
        "query": "Where are the Sender and Receiver engines for CUDA IPC frame export and import implemented as a matched pair?",
    },
    {
        "id": "B2",
        "query": "Where are the Windows and macOS secure-storage backends implemented as parallel platform-specific modules?",
    },
    {
        "id": "B3",
        "query": "Which test file exercises the multi-ControlNet residual-merge logic, and which module implements the merge it's testing?",
    },
    {
        "id": "B4",
        "query": "Where are the single-frame and multi-frame variants of the img2img and txt2img example scripts?",
    },
    {
        "id": "B5",
        "query": "Where do the shmem_in_cn_processed and shmem_out_out_ip TouchDesigner script sets mirror each other's callback structure?",
    },
    {
        "id": "B6",
        "query": "Which test exercises FaceID LoRA fusion, and which module implements FaceID compatibility handling?",
    },
    {
        "id": "C1",
        "query": "What does the StreamDiffusion pipeline class's constructor configure - CFG type, LoRA dict, KV-cache, feature injection?",
    },
    {
        "id": "C2",
        "query": "What is the architecture of the CUDA IPC extension that delegates sender and receiver work to separate engines?",
    },
    {
        "id": "C3",
        "query": "What responsibilities does the StreamDiffusionTD TouchDesigner extension class own - model management, TensorRT engine building, version tracking?",
    },
    {
        "id": "C4",
        "query": "How is the preprocessing pipeline orchestrated across ControlNet, IPAdapter, and FaceID processors?",
    },
    {
        "id": "C5",
        "query": "What is the shared-memory protocol layout - header, slot size, magic number, version - used for TouchDesigner/CUDA IPC transport?",
    },
    {
        "id": "C6",
        "query": "What does the sd_installer CLI subsystem do end to end - install, verify, report?",
    },
    {
        "id": "E1",
        "query": "How does a frame captured from a TouchDesigner TOP travel through CUDA IPC shared memory to become a texture on the receiver side?",
    },
    {
        "id": "E2",
        "query": "How does the FP8 quantization pipeline connect calibration image loading, ONNX Q/DQ node injection, and the TensorRT engine build?",
    },
    {
        "id": "E3",
        "query": "How does a ControlNet config uploaded through the FastAPI route reach the running diffusion pipeline's runtime state?",
    },
    {
        "id": "E4",
        "query": "How does the StreamDiffusionTD extension coordinate with model_utils to resolve a compatible ControlNet model for the currently loaded base model?",
    },
    {
        "id": "E5",
        "query": "How does the token stored by secure_storage get used by the tox_updater extension to authorize a TOX update download?",
    },
    {
        "id": "E6",
        "query": "How is GPU profiling threaded through both the wrapper-level FP8 calibration path and the core pipeline's per-step timing?",
    },
    {
        "id": "E7",
        "query": "How does the param_schema module's timestep-grid computation connect the wrapper's calibration index building to the pipeline's sub-timestep scheduling?",
    },
    {
        "id": "E8",
        "query": "How does the OSC message handler in Scripts route incoming control messages to the StreamDiffusionTD extension's parameter updates?",
    },
]
assert len(QUERIES) == 30, f"expected 30 pre-registered queries, got {len(QUERIES)}"


# ---------------------------------------------------------------------------
# Project-selection guard (read-only -- see mcp_server/storage_manager.py)
# ---------------------------------------------------------------------------


def resolve_project_storage(project_path: str) -> Path:
    """Locate an existing index for *project_path* without ever creating one.

    ``mcp_server.storage_manager.get_project_storage_dir`` -- what
    ``get_searcher`` calls internally -- will ``mkdir`` a fresh, empty project
    directory and write a new ``project_info.json`` if none exists yet. This
    probe must never do that (it is read-only by design). Uses the
    side-effect-free ``get_canonical_project_info`` lookup instead and aborts
    if it finds nothing, so ``get_project_storage_dir``'s write branches are
    provably never reached for this project.

    Returns:
        The project's storage directory (parent of its ``project_info.json``).

    Raises:
        SystemExit(2): No existing index found, or the stored project_path
            does not resolve to the same directory as *project_path*.
    """
    from mcp_server.storage_manager import get_canonical_project_info

    info_path = get_canonical_project_info(project_path)
    if info_path is None or not info_path.exists():
        print(
            f"ERROR: no existing index found for {project_path!r}. This probe "
            "is read-only and refuses to create one -- run index_directory "
            "first.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    with open(info_path, encoding="utf-8") as f:
        info = json.load(f)

    stored_path = Path(info.get("project_path", "")).resolve()
    requested_path = Path(project_path).resolve()
    if stored_path != requested_path:
        print(
            f"ERROR: stored project_path {stored_path} does not match "
            f"requested {requested_path} -- refusing to proceed (would need "
            "get_project_storage_dir's path-rewrite branch, which this probe "
            "does not exercise).",
            file=sys.stderr,
        )
        raise SystemExit(2)

    return info_path.parent


# ---------------------------------------------------------------------------
# Content-hash duplicate detection
# ---------------------------------------------------------------------------


def normalize_content(text: str) -> str:
    """Minimal normalization: CRLF->LF, per-line trailing-WS strip, blank-line
    strip at both ends. Deliberately no comment/docstring stripping, no
    dedent -- every extra step converts "provably identical" into "similar",
    an axis already proven non-separable (SIMILAR_DIVERSITY_20260728.md).
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = [ln.rstrip() for ln in lines]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def content_sha256(normalized_text: str) -> str:
    return hashlib.sha256(normalized_text.encode("utf-8", errors="replace")).hexdigest()


@dataclass
class ContentIndex:
    """chunk_id -> normalized-content identity, built once from the metadata
    store. Keyed by the *raw* chunk_id (with line range) exactly as stored in
    ``MetadataStore`` and exactly as it appears on ``SearchResult.chunk_id`` /
    ``RerankingEngine.last_window_ids`` -- no dedup_key stripping. Content-hash
    grouping is a strictly finer-grained signal than dedup_key (it naturally
    leaves split_block sub-range fragments distinct, since their bm25_text
    differs), so this deliberately does not reuse
    ``evaluation.metrics.normalize_chunk_id``.
    """

    sha_by_chunk: dict[str, str]
    norm_len_by_chunk: dict[str, int]  # only entries with non-empty bm25_text
    relpath_by_chunk: dict[str, str]
    text_by_chunk: dict[str, str]  # raw bm25_text, for the shingle/Jaccard tier

    def status(self, chunk_id: str, min_chars: int) -> str:
        norm_len = self.norm_len_by_chunk.get(chunk_id)
        if norm_len is None:
            return "no_content"
        if norm_len < min_chars:
            return "trivial"
        return "ok"

    def key(self, chunk_id: str, min_chars: int) -> tuple[str, str]:
        """(status, grouping_key). grouping_key is the content SHA for "ok"
        chunks; a unique per-chunk sentinel otherwise, so no_content/trivial
        entries never spuriously collide with each other."""
        status = self.status(chunk_id, min_chars)
        if status == "ok":
            return status, self.sha_by_chunk[chunk_id]
        return status, f"__{status}__:{chunk_id}"


def build_content_index(searcher: Any) -> ContentIndex:
    """Build the content index once at startup from
    ``searcher.dense_index.metadata_store.items()``.

    Uses ``metadata["bm25_text"]`` (raw, unaugmented chunk source) -- not
    ``metadata["content"]`` (path/symbol-augmented for BM25-won candidates,
    systematic false negatives on exactly the population under study) and not
    ``content_preview`` (<=200 chars, systematic false positives).
    """
    sha_by_chunk: dict[str, str] = {}
    norm_len_by_chunk: dict[str, int] = {}
    relpath_by_chunk: dict[str, str] = {}
    text_by_chunk: dict[str, str] = {}
    for chunk_id, entry in searcher.dense_index.metadata_store.items():
        metadata = entry.get("metadata", {}) if isinstance(entry, dict) else {}
        relpath_by_chunk[chunk_id] = metadata.get("relative_path", "")
        bm25_text = metadata.get("bm25_text") or ""
        if not bm25_text:
            continue  # no_content -- absent/empty bm25_text (index_sync.py:248-257)
        text_by_chunk[chunk_id] = bm25_text
        norm = normalize_content(bm25_text)
        norm_len_by_chunk[chunk_id] = len(norm)
        if norm:
            sha_by_chunk[chunk_id] = content_sha256(norm)
    return ContentIndex(
        sha_by_chunk=sha_by_chunk,
        norm_len_by_chunk=norm_len_by_chunk,
        relpath_by_chunk=relpath_by_chunk,
        text_by_chunk=text_by_chunk,
    )


def shingles(chunk_id: str, content_idx: ContentIndex) -> set[bytes]:
    """8-token whitespace-shingle set for the secondary Jaccard tier.

    Reuses ``analyze_chunking_corpus.duplication_stats``'s construction but
    replaces its ``hash()`` with ``blake2b(digest_size=8)`` -- stdlib
    ``hash()`` is process-salted (PYTHONHASHSEED) and must never be compared
    or persisted across runs. Report-only tier, never gated.
    """
    text = content_idx.text_by_chunk.get(chunk_id, "")
    tokens = text.split()
    if len(tokens) < SHINGLE_K:
        return set()
    out: set[bytes] = set()
    for i in range(len(tokens) - SHINGLE_K + 1):
        shingle = " ".join(tokens[i : i + SHINGLE_K]).encode("utf-8", errors="replace")
        out.add(hashlib.blake2b(shingle, digest_size=8).digest())
    return out


def jaccard_pair_counts(
    chunk_ids: list[str],
    content_idx: ContentIndex,
    thresholds: tuple[float, ...] = JACCARD_THRESHOLDS,
) -> dict[float, int]:
    """Pairwise Jaccard shingle overlap among a window (<=30 items, O(n^2/2)
    pairs -- cheap). Never uses difflib.SequenceMatcher (O(n^2) char-level,
    timed out past 300s on ~6,000-line class chunks in earlier hand
    measurement)."""
    shingle_sets = {cid: shingles(cid, content_idx) for cid in chunk_ids}
    counts = dict.fromkeys(thresholds, 0)
    ids = [cid for cid in chunk_ids if shingle_sets[cid]]
    for i, a in enumerate(ids):
        sa = shingle_sets[a]
        for b in ids[i + 1 :]:
            sb = shingle_sets[b]
            inter = len(sa & sb)
            if inter == 0:
                continue
            jac = inter / (len(sa) + len(sb) - inter)
            for t in thresholds:
                if jac >= t:
                    counts[t] += 1
    return counts


# ---------------------------------------------------------------------------
# Instrumentation (adapted from probe_rerank_window.py's Instrumentation)
# ---------------------------------------------------------------------------


class Instrumentation:
    """Installs/removes monkeypatches on RerankingEngine and RRFReranker
    classes to capture every rerank pass and the pre-fusion leg lists.

    Adapted from ``probe_rerank_window.py``'s ``Instrumentation``: drops the
    ``_single_hop_search`` patch (hop-1 rank not needed here), adds an
    ``RRFReranker.rerank_simple`` patch to capture pre-fusion BM25/dense leg
    lists (for the Pass-1 "refused" fusion-depth variant), and captures every
    ``_run_rerank`` pass -- not just Pass 2 -- including full candidate
    snapshots (for the real P3 re-rerank replay).

    Hazard: jina overwrites ``.score`` on SearchResult objects in place
    (neural_reranker.py) -- candidate snapshots use ``dataclasses.replace``
    at capture time so later mutation of the live objects cannot contaminate
    what was recorded.
    """

    def __init__(self, searcher: Any) -> None:
        self._engine_cls = type(searcher.reranking_engine)
        self._reranker_cls = type(searcher.reranker)
        self._orig_rerank_by_query = self._engine_cls.rerank_by_query
        self._orig_run_rerank = self._engine_cls._run_rerank
        self._orig_rerank_simple = self._reranker_cls.rerank_simple
        self.reset()

    def reset(self) -> None:
        self.rerank_by_query_calls: list[dict] = []
        self.run_rerank_calls: list[dict] = []
        self.rerank_simple_calls: list[dict] = []
        # Ordinal of the rerank_by_query call currently executing, so a nested
        # _run_rerank call (fired synchronously from inside it) can record
        # which rerank_by_query call it belongs to -- the Pass-2/Pass-3
        # disambiguation (both dispatch under MERGE_LOG_PREFIX).
        self._active_ordinal: int | None = None

    def install(self) -> None:
        instrumentation = self
        orig_rerank_by_query = self._orig_rerank_by_query
        orig_run_rerank = self._orig_run_rerank
        orig_rerank_simple = self._orig_rerank_simple

        def patched_rerank_by_query(self_engine, query, results, k, *args, **kwargs):
            ordinal = len(instrumentation.rerank_by_query_calls)
            hop1_reserved_slots = kwargs.get(
                "hop1_reserved_slots", args[1] if len(args) > 1 else 0
            )
            instrumentation.rerank_by_query_calls.append(
                {
                    "ordinal": ordinal,
                    "hop1_reserved_slots": hop1_reserved_slots,
                }
            )
            instrumentation._active_ordinal = ordinal
            try:
                output = orig_rerank_by_query(
                    self_engine, query, results, k, *args, **kwargs
                )
            finally:
                instrumentation._active_ordinal = None
            return output

        def patched_run_rerank(
            self_engine, query_or_content, candidates, k, log_prefix, config=None
        ):
            if config is None:
                from search.config import get_search_config

                config = get_search_config()
            rerank_count = min(config.reranker.top_k_candidates, len(candidates))
            window = candidates[:rerank_count]
            instrumentation.run_rerank_calls.append(
                {
                    "log_prefix": log_prefix,
                    "rerank_by_query_ordinal": instrumentation._active_ordinal,
                    "top_k_candidates": config.reranker.top_k_candidates,
                    "pool_ids": [c.chunk_id for c in candidates],
                    "window_ids": [c.chunk_id for c in window],
                    "rerank_count": rerank_count,
                    # Snapshots (dataclasses.replace) break aliasing so a later
                    # in-place .score mutation by jina cannot contaminate the
                    # capture -- these are what P3's replay re-reranks.
                    "window_snapshot": [replace(c) for c in window],
                }
            )
            return orig_run_rerank(
                self_engine, query_or_content, candidates, k, log_prefix, config=config
            )

        def patched_rerank_simple(
            self_reranker,
            bm25_results,
            dense_results,
            max_results=10,
            bm25_weight=0.35,
            dense_weight=0.65,
            reserved_slots=0,
        ):
            instrumentation.rerank_simple_calls.append(
                {
                    "reranker": self_reranker,
                    "bm25_results": list(bm25_results),
                    "dense_results": list(dense_results),
                    "max_results": max_results,
                    "bm25_weight": bm25_weight,
                    "dense_weight": dense_weight,
                    "reserved_slots": reserved_slots,
                }
            )
            return orig_rerank_simple(
                self_reranker,
                bm25_results,
                dense_results,
                max_results=max_results,
                bm25_weight=bm25_weight,
                dense_weight=dense_weight,
                reserved_slots=reserved_slots,
            )

        self._engine_cls.rerank_by_query = patched_rerank_by_query
        self._engine_cls._run_rerank = patched_run_rerank
        self._reranker_cls.rerank_simple = patched_rerank_simple

    def uninstall(self) -> None:
        self._engine_cls.rerank_by_query = self._orig_rerank_by_query
        self._engine_cls._run_rerank = self._orig_run_rerank
        self._reranker_cls.rerank_simple = self._orig_rerank_simple

    def classify_passes(self) -> dict[str, list[dict]]:
        """Split captured _run_rerank calls into pass1/pass2/pass3 by log
        prefix + nested-call ordinal (see module docstring)."""
        pass2_ordinal = None
        for call in self.rerank_by_query_calls:
            if call["hop1_reserved_slots"] > 0:
                pass2_ordinal = call["ordinal"]
                break  # only MultiHopSearcher's Pass-2 call ever passes >0

        pass1, pass2, pass3 = [], [], []
        for rc in self.run_rerank_calls:
            if rc["log_prefix"] != MERGE_LOG_PREFIX:
                pass1.append(rc)
            elif (
                rc["rerank_by_query_ordinal"] == pass2_ordinal
                and pass2_ordinal is not None
            ):
                pass2.append(rc)
            else:
                pass3.append(rc)
        return {"pass1": pass1, "pass2": pass2, "pass3": pass3}


# ---------------------------------------------------------------------------
# Dedup-aware walk (structural clone of
# RerankingEngine._apply_graph_hop_window_cap)
# ---------------------------------------------------------------------------


def dedup_aware_walk(
    pool_ids: list[str], content_idx: ContentIndex, window_size: int, min_chars: int
) -> dict[str, Any]:
    """Single stable pass over the pool in its existing (pre-cut) order:
    admit a chunk unless a chunk with the same normalized-content hash has
    already been admitted; defer duplicates to just below the window so
    later, content-distinct candidates backfill the freed slots. Output is
    always a permutation of the input (window + deferred + untouched tail) --
    same shape as ``_apply_graph_hop_window_cap``.
    """
    window: list[str] = []
    deferred: list[str] = []
    admitted_shas: set[str] = set()
    stopped_at = len(pool_ids)
    for idx, chunk_id in enumerate(pool_ids):
        if len(window) == window_size:
            stopped_at = idx
            break
        status, key = content_idx.key(chunk_id, min_chars)
        if status == "ok" and key in admitted_shas:
            deferred.append(chunk_id)
        else:
            if status == "ok":
                admitted_shas.add(key)
            window.append(chunk_id)
    return {
        "window": window,
        "deferred": deferred,
        "permutation": window + deferred + pool_ids[stopped_at:],
    }


def window_dup_stats(
    window_ids: list[str], content_idx: ContentIndex, min_chars: int
) -> dict[str, Any]:
    """win_dup_slots/win_dup_groups/win_dup_pct/content_cov for one observed
    window, at one MIN_NORM_CHARS threshold."""
    groups: dict[str, list[str]] = {}
    no_content = trivial = 0
    for cid in window_ids:
        status, key = content_idx.key(cid, min_chars)
        if status == "no_content":
            no_content += 1
        elif status == "trivial":
            trivial += 1
        groups.setdefault(key, []).append(cid)

    dup_groups = {
        k: v for k, v in groups.items() if len(v) > 1 and not k.startswith("__")
    }
    dup_slots = sum(len(v) - 1 for v in dup_groups.values())
    win_n = len(window_ids)
    covered = win_n - no_content
    return {
        "win_n": win_n,
        "win_dup_slots": dup_slots,
        "win_dup_groups": len(dup_groups),
        "win_dup_pct": round(dup_slots / win_n, 4) if win_n else 0.0,
        "content_cov": round(covered / win_n, 4) if win_n else 0.0,
        "no_content": no_content,
        "trivial": trivial,
        "dup_group_members": dup_groups,  # for P4 pair printing
    }


# ---------------------------------------------------------------------------
# Per-query probing
# ---------------------------------------------------------------------------


def _new_files_from_walk(
    walk_window: list[str], observed_window: list[str], content_idx: ContentIndex
) -> tuple[int, int]:
    observed_set = set(observed_window)
    observed_files = {content_idx.relpath_by_chunk.get(c, "") for c in observed_window}
    admitted_new = [c for c in walk_window if c not in observed_set]
    new_files = {
        content_idx.relpath_by_chunk.get(c, "")
        for c in admitted_new
        if content_idx.relpath_by_chunk.get(c, "") not in observed_files
    }
    return len(admitted_new), len(new_files)


def _pass1_refused(
    instrumentation: Instrumentation,
    content_idx: ContentIndex,
    min_chars: int,
) -> dict[str, Any] | None:
    """Replay the captured pre-fusion BM25/dense leg lists through the real
    (pure-function, offline) RRFReranker.rerank_simple at max_results=60,
    then run the dedup-aware walk against that deeper pool. At Pass 1 the
    observed window IS the fused pool (fusion_k = max(k, reranker_budget)),
    so backfill_avail is structurally 0 there -- this variant asks what
    Pass 1 would look like with a deeper fusion cut, flagged
    requires_fusion_k>30."""
    if not instrumentation.rerank_simple_calls:
        return None
    call = instrumentation.rerank_simple_calls[0]
    deep_results = call["reranker"].rerank_simple(
        bm25_results=call["bm25_results"],
        dense_results=call["dense_results"],
        max_results=60,
        bm25_weight=call["bm25_weight"],
        dense_weight=call["dense_weight"],
        reserved_slots=call["reserved_slots"],
    )
    deep_ids = [r.chunk_id for r in deep_results]
    walk = dedup_aware_walk(deep_ids, content_idx, window_size=30, min_chars=min_chars)
    observed_window = deep_ids[:30]
    admitted_new, new_files = _new_files_from_walk(
        walk["window"], observed_window, content_idx
    )
    return {
        "requires_fusion_k_gt_30": True,
        "deep_pool_n": len(deep_ids),
        "admitted_new": admitted_new,
        "new_files": new_files,
    }


def probe_query(
    searcher: Any,
    reranker_instance: Any,
    query_item: dict[str, str],
    content_idx: ContentIndex,
    k: int,
    config: Any,
    min_chars: int = MIN_NORM_CHARS_DEFAULT,
) -> dict[str, Any]:
    """Run one query with instrumentation installed; return per-pass rows
    plus G0/P2/P3/P4 raw material for gate evaluation."""
    instrumentation = Instrumentation(searcher)
    instrumentation.install()
    try:
        query = query_item["query"]
        final_results = searcher.search(query, k=k, config=config)
    finally:
        instrumentation.uninstall()

    passes = instrumentation.classify_passes()
    engine_last_window = list(searcher.reranking_engine.last_window_ids or [])

    if not any(passes.values()):
        return {
            "id": query_item["id"],
            "reranker_skipped": True,
            "rows": [],
        }

    rows: list[dict[str, Any]] = []
    last_pass_call: dict | None = None
    last_pass_name = None
    for pass_name in ("pass1", "pass2", "pass3"):
        calls = passes[pass_name]
        if not calls:
            continue
        # One call expected per pass per query; if more than one fires
        # (e.g. multi-hop with >1 hop-level search), take the last -- it is
        # the one whose output actually reaches the final merged pool.
        call = calls[-1]
        last_pass_call = call
        last_pass_name = pass_name

        window_ids = call["window_ids"]
        pool_ids = call["pool_ids"]
        stats = window_dup_stats(window_ids, content_idx, min_chars)
        walk = dedup_aware_walk(
            pool_ids, content_idx, window_size=len(window_ids), min_chars=min_chars
        )
        backfill_avail = len(pool_ids) - len(window_ids)
        admitted_new, new_files = (0, 0)
        if pass_name != "pass1" and backfill_avail > 0:
            admitted_new, new_files = _new_files_from_walk(
                walk["window"], window_ids, content_idx
            )

        jac = jaccard_pair_counts(window_ids, content_idx)
        rows.append(
            {
                "qid": query_item["id"],
                "pass": pass_name,
                "pool_n": len(pool_ids),
                "win_n": stats["win_n"],
                "win_dup_slots": stats["win_dup_slots"],
                "win_dup_groups": stats["win_dup_groups"],
                "win_dup_pct": stats["win_dup_pct"],
                "backfill_avail": backfill_avail,
                "admitted_new": admitted_new,
                "new_files": new_files,
                "content_cov": stats["content_cov"],
                "no_content": stats["no_content"],
                "trivial": stats["trivial"],
                "j80_pairs": jac.get(0.8, 0),
                "j90_pairs": jac.get(0.9, 0),
                "dup_group_members": stats["dup_group_members"],
                "window_ids": window_ids,
            }
        )

    g0_window_match = (
        last_pass_call is not None
        and last_pass_call["window_ids"] == engine_last_window
    )
    g0_content_cov_ok = all(r["content_cov"] >= G0_MIN_CONTENT_COV for r in rows)

    pass1_refused = None
    if "pass1" in [r["pass"] for r in rows]:
        pass1_refused = _pass1_refused(instrumentation, content_idx, min_chars)

    observed_top7 = [r.chunk_id for r in final_results[:7]]

    return {
        "id": query_item["id"],
        "reranker_skipped": False,
        "rows": rows,
        "g0_window_match": g0_window_match,
        "g0_content_cov_ok": g0_content_cov_ok,
        "last_pass_name": last_pass_name,
        "last_pass_window_snapshot": last_pass_call["window_snapshot"]
        if last_pass_call
        else [],
        "pass1_refused": pass1_refused,
        "observed_top7": observed_top7,
        "reranking_engine": searcher.reranking_engine,
    }


def run_p3_replay(
    query_item: dict[str, str],
    report: dict[str, Any],
    content_idx: ContentIndex,
    k: int,
    min_chars: int = MIN_NORM_CHARS_DEFAULT,
) -> dict[str, Any] | None:
    """Re-run the real (live, loaded) cross-encoder on the dedup-aware
    permutation of the last pass's window, apply dedupe_results, and compare
    the resulting top-7 against the observed top-7. jina scores the window
    jointly -- this can only show the top-7 *changed*, never *improved*
    (no gold labels for these 30 queries)."""
    from search.chunk_id import dedupe_results

    snapshot = report["last_pass_window_snapshot"]
    if not snapshot:
        return None
    by_id = {c.chunk_id: c for c in snapshot}
    window_ids = [c.chunk_id for c in snapshot]
    walk = dedup_aware_walk(
        window_ids, content_idx, window_size=len(window_ids), min_chars=min_chars
    )
    dedup_window = [by_id[cid] for cid in walk["window"] if cid in by_id]

    engine = report["reranking_engine"]
    neural_reranker = engine.neural_reranker
    if neural_reranker is None or not dedup_window:
        return None

    reranked = neural_reranker.rerank(query_item["query"], dedup_window, k)
    reranked = dedupe_results(reranked)
    new_top7 = [r.chunk_id for r in reranked[:7]]
    observed_top7 = report["observed_top7"]

    newly_displayed = [cid for cid in new_top7 if cid not in observed_top7]
    return {
        "changed": new_top7 != observed_top7,
        "new_top7": new_top7,
        "newly_displayed_count": len(newly_displayed),
        "newly_displayed": newly_displayed,
    }


# ---------------------------------------------------------------------------
# Gate evaluation
# ---------------------------------------------------------------------------


def evaluate_gate(
    reports: list[dict[str, Any]],
    p3_replays: dict[str, dict[str, Any] | None],
) -> dict[str, Any]:
    pass2_rows = [
        r for rep in reports for r in rep.get("rows", []) if r["pass"] == "pass2"
    ]

    # G0
    g0_ok = all(
        rep.get("g0_window_match", False) and rep.get("g0_content_cov_ok", False)
        for rep in reports
        if not rep.get("reranker_skipped")
    )
    skipped = [rep["id"] for rep in reports if rep.get("reranker_skipped")]

    # P1
    p1_slots = sum(r["win_dup_slots"] for r in pass2_rows)
    p1_per_query = [r["win_dup_slots"] for r in pass2_rows]
    p1_median = median(p1_per_query) if p1_per_query else 0
    p1_ok = p1_slots >= GATE_P1_MIN_SLOTS and p1_median >= GATE_P1_MIN_MEDIAN

    # P2 (Pass 2 + Pass 3 only, Pass 1 structurally excluded)
    p2_rows = [
        r
        for rep in reports
        for r in rep.get("rows", [])
        if r["pass"] in ("pass2", "pass3")
    ]
    p2_admitted = sum(r["admitted_new"] for r in p2_rows)
    p2_new_files = sum(r["new_files"] for r in p2_rows)
    p2_ok = (
        p2_admitted >= GATE_P2_MIN_ADMITTED and p2_new_files >= GATE_P2_MIN_NEW_FILES
    )

    # P3
    changed_queries = [
        qid for qid, rep_ in p3_replays.items() if rep_ and rep_["changed"]
    ]
    p3_new_chunks = sum(
        rep_["newly_displayed_count"] for rep_ in p3_replays.values() if rep_
    )
    p3_ok = (
        len(changed_queries) >= GATE_P3_MIN_QUERIES_CHANGED
        and p3_new_chunks >= GATE_P3_MIN_NEW_CHUNKS
    )

    # P4: B-category collapsed-pair canary
    b_collapsed = 0
    b_pairs: list[dict] = []
    for rep in reports:
        if not any(rep["id"].startswith(p) for p in B_CATEGORY_PREFIXES):
            continue
        for row in rep.get("rows", []):
            if row["pass"] != "pass2":
                continue
            for sha, members in row["dup_group_members"].items():
                if sha.startswith("__"):
                    continue
                b_collapsed += len(members) - 1
                b_pairs.append({"qid": rep["id"], "sha": sha, "members": members})
    p4_ok = b_collapsed < p3_new_chunks  # ABORT if B-category collapses >= P3's gains

    overall = g0_ok and p1_ok and p2_ok and p3_ok and p4_ok
    return {
        "g0_ok": g0_ok,
        "g0_skipped_queries": skipped,
        "p1_ok": p1_ok,
        "p1_slots": p1_slots,
        "p1_denominator": len(pass2_rows) * 30,
        "p1_median": p1_median,
        "p2_ok": p2_ok,
        "p2_admitted": p2_admitted,
        "p2_new_files": p2_new_files,
        "p3_ok": p3_ok,
        "p3_changed_queries": changed_queries,
        "p3_new_chunks": p3_new_chunks,
        "p4_ok": p4_ok,
        "p4_b_collapsed": b_collapsed,
        "p4_b_pairs": b_pairs,
        "overall": overall,
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def build_arm_a_config(leg_multiplier: int) -> Any:
    """Reconstruct Arm A in memory: reranker.enabled=True,
    top_k_candidates=30, intent.enabled=True, leg_search_multiplier as given.
    Mutates the config singleton in place via arm_overrides.apply_overrides
    (in-place attribute mutation, no file write, no object swap) -- never
    touches search_config.json, which stays in its ablated Arm-B state.
    """
    from evaluation import arm_overrides
    from search.config import get_search_config

    cfg = get_search_config()
    arm_overrides.apply_overrides(
        cfg,
        {
            "reranker.enabled": True,
            "reranker.top_k_candidates": 30,
            "intent.enabled": True,
            "search_mode.leg_search_multiplier": leg_multiplier,
        },
    )
    if not cfg.reranker.enabled or cfg.reranker.top_k_candidates != 30:
        print(
            "ERROR: Arm-A reconstruction failed -- reranker.enabled="
            f"{cfg.reranker.enabled}, top_k_candidates={cfg.reranker.top_k_candidates}",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return cfg


def run_probe(
    project_path: str,
    k: int,
    leg_multiplier: int,
    min_chars: int = MIN_NORM_CHARS_DEFAULT,
) -> dict[str, Any]:
    from mcp_server.search_factory import get_searcher
    from search.config import set_active_project_storage_dir

    storage_dir = resolve_project_storage(project_path)
    set_active_project_storage_dir(str(storage_dir))
    cfg = build_arm_a_config(leg_multiplier)

    print(
        f"[ARM-A] reranker.enabled={cfg.reranker.enabled} "
        f"top_k_candidates={cfg.reranker.top_k_candidates} "
        f"intent.enabled={cfg.intent.enabled} "
        f"leg_search_multiplier={cfg.search_mode.leg_search_multiplier} "
        f"multi_hop.enabled={cfg.multi_hop.enabled} "
        f"ego_graph.enabled={cfg.ego_graph.enabled}"
    )

    searcher = get_searcher(project_path=project_path)
    content_idx = build_content_index(searcher)
    print(
        f"[CONTENT-INDEX] {len(content_idx.sha_by_chunk)} chunks with usable "
        f"bm25_text of {len(content_idx.relpath_by_chunk)} total"
    )

    reports = []
    p3_replays: dict[str, dict[str, Any] | None] = {}
    for i, item in enumerate(QUERIES, 1):
        print(f"[{i:2d}/{len(QUERIES)}] {item['id']}", flush=True)
        rep = probe_query(
            searcher, searcher.reranker, item, content_idx, k, cfg, min_chars
        )
        reports.append(rep)
        if not rep.get("reranker_skipped"):
            p3_replays[item["id"]] = run_p3_replay(item, rep, content_idx, k, min_chars)
        else:
            p3_replays[item["id"]] = None

    gate = evaluate_gate(reports, p3_replays)

    # Sensitivity: total dup_slots summed over ALL captured windows at each
    # MIN_NORM_CHARS threshold (recomputed cheaply from window_ids already
    # captured in rows[0]'s pass, using window_dup_stats directly).
    sensitivity = {}
    for mc in MIN_NORM_CHARS_SENSITIVITY:
        total = 0
        for rep in reports:
            for row in rep.get("rows", []):
                stats = window_dup_stats(row["window_ids"], content_idx, mc)
                total += stats["win_dup_slots"]
        sensitivity[mc] = total

    return {
        "leg_multiplier": leg_multiplier,
        "k": k,
        "min_chars": min_chars,
        "reports": [
            {k2: v for k2, v in rep.items() if k2 not in ("reranking_engine",)}
            for rep in reports
        ],
        "p3_replays": p3_replays,
        "gate": gate,
        "sensitivity": sensitivity,
    }


def print_report(result: dict[str, Any]) -> None:
    gate = result["gate"]
    print(f"\n=== leg_search_multiplier={result['leg_multiplier']} k={result['k']} ===")
    print(
        f"{'qid':>4} {'pass':>5} {'pool_n':>6} {'win_n':>5} {'dup_slots':>9} "
        f"{'dup_pct':>7} {'backfill':>8} {'admit_new':>9} {'new_files':>9} {'cov':>5}"
    )
    for rep in result["reports"]:
        if rep.get("reranker_skipped"):
            print(f"{rep['id']:>4}  RERANKER SKIPPED (VRAM gate or reranker disabled)")
            continue
        for row in rep["rows"]:
            print(
                f"{row['qid']:>4} {row['pass']:>5} {row['pool_n']:>6} {row['win_n']:>5} "
                f"{row['win_dup_slots']:>9} {row['win_dup_pct']:>7.2%} "
                f"{row['backfill_avail']:>8} {row['admitted_new']:>9} "
                f"{row['new_files']:>9} {row['content_cov']:>5.2f}"
            )

    print("\n--- Sensitivity (total dup_slots across ALL captured windows) ---")
    for mc, total in result["sensitivity"].items():
        print(f"  MIN_NORM_CHARS={mc:>4}: {total}")

    print("\n--- Gate ---")
    print(
        f"  G0 self-validity: {'PASS' if gate['g0_ok'] else 'FAIL'} "
        f"(skipped: {gate['g0_skipped_queries']})"
    )
    print(
        f"  P1 window occupancy: {'PASS' if gate['p1_ok'] else 'FAIL'} "
        f"({gate['p1_slots']}/{gate['p1_denominator']} slots, "
        f"median={gate['p1_median']}, need >={GATE_P1_MIN_SLOTS} & median>={GATE_P1_MIN_MEDIAN})"
    )
    print(
        f"  P2 recoverability: {'PASS' if gate['p2_ok'] else 'FAIL'} "
        f"(admitted_new={gate['p2_admitted']}, new_files={gate['p2_new_files']}, "
        f"need >={GATE_P2_MIN_ADMITTED} & >={GATE_P2_MIN_NEW_FILES})"
    )
    print(
        f"  P3 display conversion: {'PASS' if gate['p3_ok'] else 'FAIL'} "
        f"(changed_queries={len(gate['p3_changed_queries'])}/30 {gate['p3_changed_queries']}, "
        f"new_chunks={gate['p3_new_chunks']}, "
        f"need >={GATE_P3_MIN_QUERIES_CHANGED} queries & >={GATE_P3_MIN_NEW_CHUNKS} chunks)"
    )
    print(
        f"  P4 B-category canary: {'PASS' if gate['p4_ok'] else 'ABORT'} "
        f"(b_collapsed={gate['p4_b_collapsed']} vs p3_new_chunks={gate['p3_new_chunks']})"
    )
    for pair in gate["p4_b_pairs"]:
        print(f"    [B-CANARY] {pair['qid']}: {pair['members']}")

    print(f"\n  OVERALL: {'PASS' if gate['overall'] else 'ABORT'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project-path", default="D:\\dev\\SDTD_040_Beta")
    parser.add_argument(
        "--k",
        type=int,
        default=10,
        help="matches cross-system harness parity: request top-10",
    )
    parser.add_argument(
        "--leg-multiplier",
        choices=("1", "5", "both"),
        default="both",
        help="which leg_search_multiplier to test (Arm-A ambiguity, see plan)",
    )
    parser.add_argument("--min-chars", type=int, default=MIN_NORM_CHARS_DEFAULT)
    parser.add_argument("--json-out", default=None)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="smoke-test only: cap the number of queries run (skips the gate)",
    )
    args = parser.parse_args()

    if args.limit is not None:
        del QUERIES[args.limit :]

    multipliers = (
        [1, 5] if args.leg_multiplier == "both" else [int(args.leg_multiplier)]
    )

    results = {}
    for m in multipliers:
        results[m] = run_probe(args.project_path, args.k, m, args.min_chars)
        print_report(results[m])

    exit_code = 0
    for m, result in results.items():
        if not (result["gate"]["g0_ok"]):
            print(f"\n[HALT] G0 self-validity failed at leg_search_multiplier={m}")
            exit_code = 3
        if not result["gate"]["overall"]:
            exit_code = max(exit_code, 1) if exit_code != 3 else exit_code

    if len(multipliers) == 2:
        r1, r5 = results[1]["gate"], results[5]["gate"]
        # "Diverge materially": P1 slot totals differ by more than the smaller
        # gate margin itself (GATE_P1_MIN_SLOTS), or the two runs disagree on
        # overall pass/fail.
        slot_delta = abs(r1["p1_slots"] - r5["p1_slots"])
        if r1["overall"] != r5["overall"] or slot_delta > GATE_P1_MIN_SLOTS:
            print(
                f"\n[HALT] leg_search_multiplier=1 vs =5 diverge materially "
                f"(P1 slots {r1['p1_slots']} vs {r5['p1_slots']}, "
                f"overall {r1['overall']} vs {r5['overall']}) -- Arm-A tables "
                "cannot be reconciled with either value."
            )
            exit_code = 3

    if args.json_out:
        # SearchResult objects and content_idx aren't JSON-serializable as-is;
        # reports/gate/sensitivity dicts already are.
        payload = {
            str(m): {
                "leg_multiplier": r["leg_multiplier"],
                "k": r["k"],
                "min_chars": r["min_chars"],
                "gate": r["gate"],
                "sensitivity": r["sensitivity"],
                "p3_replays": r["p3_replays"],
                "reports": [
                    {
                        "id": rep["id"],
                        "reranker_skipped": rep.get("reranker_skipped", False),
                        "rows": [
                            {
                                k2: v2
                                for k2, v2 in row.items()
                                if k2 not in ("dup_group_members",)
                            }
                            for row in rep.get("rows", [])
                        ],
                        "g0_window_match": rep.get("g0_window_match"),
                        "g0_content_cov_ok": rep.get("g0_content_cov_ok"),
                        "observed_top7": rep.get("observed_top7"),
                    }
                    for rep in r["reports"]
                ],
            }
            for m, r in results.items()
        }
        Path(args.json_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nJSON written to {args.json_out}")

    return exit_code


if __name__ == "__main__":
    _ensure_pinned_hash_seed()
    sys.exit(main())
