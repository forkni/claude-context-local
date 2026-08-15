"""Auto-tuning probe stage for full reindex (ADR-0014).

Two passes run during a *full* (non-incremental) reindex and persist their
findings to ``<project_storage_dir>/search_overrides.json`` — the per-project
override layer merged by ``search.config`` (precedence: env > per-project >
global file > dataclass defaults):

- **Pass 1** (``probe_pre_chunking``, hook A in
  ``IncrementalIndexer._full_index``, before chunking starts): measures
  hardware (VRAM/CPU) and corpus shape (file count, extension histogram,
  repo profile) and emits **overrides** for safe hardware/corpus-structural
  knobs only. It overwrites the file wholesale so stale provenance never
  lingers, and writes *before* the pipeline's next ``get_search_config()``
  call so the current run already sees the merged values.
- **Pass 2** (``probe_post_build``, hook B in the index handler, after the
  index is written): reads only already-persisted ``stats.json`` data and
  appends **observations** (report-only notes) — no fresh graph analysis.

Retrieval-quality knobs are never auto-tuned (no golden dataset exists on
arbitrary projects); benchmark-validated keys are pinned in
``FORBIDDEN_AUTO_TUNE_KEYS`` and a static unit test asserts no override rule
touches them.  Overrides for ``performance.max_chunking_workers`` /
``performance.enable_parallel_chunking`` bind to indexer instance attributes
at construction, so they take effect on the NEXT reindex, not the current
run (acceptable: hardware is stable between runs).

Incremental reindexes never call the probe; an existing overrides file keeps
applying untouched.  Escape hatches: ``CLAUDE_DISABLE_PROJECT_OVERRIDES=1``
env var or ``performance.enable_project_overrides=false`` in the global
config — both silence the probe entirely.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from .config import (
    PROJECT_OVERRIDES_FILENAME,
    get_search_config,
)
from .vram_manager import VRAM_TIERS, VRAMTier


if TYPE_CHECKING:
    from chunking.repo_profiler import RepoProfile


logger = logging.getLogger(__name__)

PROBE_VERSION = "1"  # bump when RULES changes

# All eight GLSL extensions (chunking/language_registry.py EXT_TO_LANGUAGE).
GLSL_EXTENSIONS = frozenset(
    {".glsl", ".frag", ".vert", ".comp", ".geom", ".tesc", ".tese", ".glslinc"}
)

# Benchmark-validated keys the probe must NEVER auto-tune (see the guardrail
# static test).  Each was pinned by an A/B on this repo's golden set — a probe
# has no golden set on arbitrary projects, so these stay human decisions:
# fusion weights/rrf_k/bm25_k1/bm25_b saturated; bm25_use_stopwords A/B'd;
# centrality_alpha 0.0 replicated; single_pass kills recall; hop1_reserved_slots
# ADR-0013; bm25_reserved_slots rejected; query_expansion ADR-0012 closed FAIL;
# bm25_tokenizer is INDEX_VERSION 4; multi_hop tuned; doc_representation_mode
# rejected 2026-08-14; merged_pool_policy rejected 2026-08-15;
# graph_hop_window_cap rejected 2026-08-15. See BENCHMARK_LOCK_CITATIONS
# below for the per-key citation (ADR-0022) shown in start_mcp_server.cmd's
# ":tuned_parameters" menu.
FORBIDDEN_AUTO_TUNE_KEYS = frozenset(
    {
        "search_mode.bm25_weight",
        "search_mode.dense_weight",
        "search_mode.rrf_k_parameter",
        "search_mode.bm25_k1",
        "search_mode.bm25_b",
        "search_mode.bm25_use_stopwords",
        "search_mode.bm25_tokenizer",
        "search_mode.bm25_reserved_slots",
        "graph_enhanced.centrality_alpha",
        "reranker.single_pass",
        "reranker.hop1_reserved_slots",
        "reranker.doc_representation_mode",
        "reranker.merged_pool_policy",
        "reranker.graph_hop_window_cap",
        "query_expansion.enabled",
        "multi_hop.expansion",
        "multi_hop.multi_hop_mode",
        "embedding.model_name",  # routes to a different per-model index dir
    }
)

# Human-readable "why this is locked" citation for each FORBIDDEN_AUTO_TUNE_KEYS
# entry, keyed identically — consumed by start_mcp_server.cmd's ":tuned_parameters"
# menu (ADR-0022) so the Benchmark-Locked panel has no second hand-typed list to
# drift out of sync with the frozenset above. "embedding.model_name" is
# deliberately excluded: it is locked for index-routing safety (see the comment
# on the frozenset), not a benchmark result, and is displayed separately under
# that menu's "Observation only" section.
BENCHMARK_LOCK_CITATIONS: dict[str, str] = {
    "search_mode.bm25_weight": "ADR-0019 (intent-adaptive fusion rejected, static weights kept)",
    "search_mode.dense_weight": "ADR-0019 (intent-adaptive fusion rejected, static weights kept)",
    "search_mode.rrf_k_parameter": "fusion sweep saturated, do not re-sweep",
    "search_mode.bm25_k1": "fusion sweep saturated",
    "search_mode.bm25_b": "fusion sweep saturated",
    "search_mode.bm25_use_stopwords": "A/B 2026-08-01: removing regresses recall@5/MRR",
    "search_mode.bm25_tokenizer": "INDEX_VERSION 4 (identifier-preserving 'whole' tokenizer)",
    "search_mode.bm25_reserved_slots": "rejected 2026-07-28 (9/9 sweep runs, no Q12 pool_hit)",
    "graph_enhanced.centrality_alpha": "higher alphas cost recall (replicated)",
    "reranker.single_pass": "kills recall; latency knob only, not quality",
    "reranker.hop1_reserved_slots": "ADR-0013",
    "reranker.doc_representation_mode": (
        "signature_head rejected 2026-08-14 (REMAINING_LEVERS_AB: recall@10/20 "
        "CI-negative on 133q, 11 pool_hit losses vs 2 gains)"
    ),
    "query_expansion.enabled": "ADR-0012 re-eval closed 2026-08-02, stays disabled",
    "multi_hop.expansion": "expansion_factor stays 0.5 (0.25 arm rejected 2026-08-02)",
    "multi_hop.multi_hop_mode": "tuned; do not re-tune without a new A/B",
    "reranker.merged_pool_policy": (
        "POOL_ORDER_AB_20260815: channel_priority breaches 63q MRR/recall@5 "
        "guard-rail; score_reserve_fix never clears the recall CI upside bar"
    ),
    "reranker.graph_hop_window_cap": (
        "POOL_ORDER_CAP_AB_20260815: neither cap=2 nor cap=3 clears the "
        "133q recall@10/recall@20 upside CI (both include zero, both point "
        "estimates negative)"
    ),
}


@dataclass(frozen=True)
class ProbeMeasurements:
    """Immutable snapshot of everything the rule table may consult.

    All fields are cheap (already in memory or a single CUDA query); rules
    must tolerate ``None`` for every optional field.
    """

    vram_total_gb: float | None  # None = no CUDA GPU
    vram_free_gb: float | None
    gpu_bf16_supported: bool | None  # None = no CUDA GPU
    cpu_count: int
    file_count: int
    language_histogram: dict[str, int]  # extension -> file count
    repo_profile: RepoProfile | None  # None unless sizing_mode == "adaptive"
    embedding_model: str | None = None  # active embedder model name
    stats: dict[str, Any] | None = None  # persisted stats.json (post_build only)


@dataclass(frozen=True)
class ProbeRule:
    """One declarative probe rule: pure functions over ``ProbeMeasurements``.

    ``kind="override"`` rules emit a config value into ``overrides`` plus a
    provenance string into ``reasons`` (keys match 1:1).  ``kind="observation"``
    rules emit a report-only note (``value_fn`` must be ``None``).
    """

    key: str  # dotted config key ("performance.max_chunking_workers")
    kind: Literal["override", "observation"]
    stage: Literal["pre_chunking", "post_build"]
    condition: Callable[[ProbeMeasurements], bool]
    value_fn: Callable[[ProbeMeasurements], Any] | None
    reason_fn: Callable[[ProbeMeasurements], str]


@dataclass
class ProbeResult:
    """Aggregated output of one rule-table pass."""

    overrides: dict[str, Any] = field(default_factory=dict)  # nested config dict
    reasons: dict[str, str] = field(default_factory=dict)  # dotted key -> reason
    observations: list[dict[str, str]] = field(default_factory=list)

    def summary(self, stage: str) -> dict[str, Any]:
        """Compact dict for logging and the MCP index response."""
        return {
            "stage": stage,
            "probe_version": PROBE_VERSION,
            "override_keys": sorted(self.reasons),
            "reasons": dict(self.reasons),
            "observation_keys": [o["key"] for o in self.observations],
        }


# ---------------------------------------------------------------------------
# Rule helpers (pure; shared between value_fn and reason_fn so reasons always
# quote the value actually applied)
# ---------------------------------------------------------------------------


def _tier_for(vram_total_gb: float | None) -> VRAMTier | None:
    """Map total VRAM to the vram_manager tier table (None = no GPU)."""
    if vram_total_gb is None:
        return None
    for tier in VRAM_TIERS:
        if tier.min_vram_gb <= vram_total_gb < tier.max_vram_gb:
            return tier
    return VRAM_TIERS[0]


def _has_gpu(m: ProbeMeasurements) -> bool:
    return m.vram_total_gb is not None


def _embedding_batch_size(m: ProbeMeasurements) -> int:
    """Fallback embed batch (used when dynamic sizing is off), VRAM-tiered."""
    vram = m.vram_total_gb or 0.0
    if vram < 6:
        return 32
    if vram < 10:
        return 64
    if vram < 18:
        return 128
    return 256


def _dynamic_batch_max(m: ProbeMeasurements) -> int:
    """Ceiling for GPU-based dynamic batch sizing, VRAM-tiered."""
    vram = m.vram_total_gb or 0.0
    if vram < 6:
        return 96
    if vram < 10:
        return 192
    if vram < 18:
        return 384
    return 512


def _chunking_workers(m: ProbeMeasurements) -> int:
    """Half the cores, capped at 16 and at the file count (floor 1)."""
    return max(1, min(m.cpu_count // 2, 16, max(m.file_count, 1)))


def _reranker_below_floor(m: ProbeMeasurements) -> bool:
    """True when the tier table says neural reranking should be off (no GPU or minimal tier)."""
    tier = _tier_for(m.vram_total_gb)
    return tier is None or not tier.neural_reranking_enabled


def _reranker_squeezed(m: ProbeMeasurements) -> bool:
    """Laptop band (6-10 GB): reranking on, but VRAM-squeezed."""
    tier = _tier_for(m.vram_total_gb)
    return tier is not None and tier.name == "laptop"


def _stats_total_chunks(m: ProbeMeasurements) -> int:
    return int((m.stats or {}).get("total_chunks", 0) or 0)


def _stats_split_share(m: ProbeMeasurements) -> float:
    total = _stats_total_chunks(m)
    if not total:
        return 0.0
    split = int(((m.stats or {}).get("chunk_types") or {}).get("split_block", 0) or 0)
    return split / total


def _stats_chunks_per_file(m: ProbeMeasurements) -> float:
    files = int((m.stats or {}).get("files_indexed", 0) or 0)
    if not files:
        return 0.0
    return _stats_total_chunks(m) / files


def _glsl_present(m: ProbeMeasurements) -> bool:
    return any(ext in GLSL_EXTENSIONS for ext in m.language_histogram)


def _reranker_below_floor_reason(m: ProbeMeasurements) -> str:
    if m.vram_total_gb is None:
        return "no CUDA GPU detected -> neural reranking disabled"
    tier = _tier_for(m.vram_total_gb)
    assert tier is not None  # _tier_for always resolves a tier for non-None VRAM
    return (
        f"vram_total={m.vram_total_gb:.1f}GB below "
        f"{tier.name} tier reranking floor -> disabled"
    )


def _embedding_model_mismatch(m: ProbeMeasurements) -> bool:
    if m.embedding_model is None:
        return False
    tier = _tier_for(m.vram_total_gb)
    return tier is not None and tier.recommended_model != m.embedding_model


def _embedding_model_reason(m: ProbeMeasurements) -> str:
    tier = _tier_for(m.vram_total_gb)
    assert tier is not None  # guarded by _embedding_model_mismatch's condition
    return (
        f"VRAM tier '{tier.name}' recommends "
        f"{tier.recommended_model} "
        f"(current: {m.embedding_model}); switching routes to a different "
        "per-model index dir — manual decision, never auto-applied"
    )


def _max_split_chars_reason(m: ProbeMeasurements) -> str:
    profile = m.repo_profile
    assert profile is not None  # guarded by the rule's condition
    return (
        f"P90 function size {profile.p90_chars} chars is >2x the "
        "split threshold — many functions will be split; consider "
        "sizing_mode=adaptive or a higher max_split_chars"
    )


# ---------------------------------------------------------------------------
# Rule table — versioned via PROBE_VERSION; every entry is pure over
# ProbeMeasurements.  Overrides = safe hardware/corpus-structural knobs only.
# ---------------------------------------------------------------------------

RULES: tuple[ProbeRule, ...] = (
    # --- Pass 1: hardware overrides -------------------------------------
    ProbeRule(
        key="embedding.batch_size",
        kind="override",
        stage="pre_chunking",
        condition=_has_gpu,
        value_fn=_embedding_batch_size,
        reason_fn=lambda m: (
            f"vram_total={m.vram_total_gb:.1f}GB -> fallback batch "
            f"{_embedding_batch_size(m)} (used when dynamic sizing disabled)"
        ),
    ),
    ProbeRule(
        key="performance.dynamic_batch_max",
        kind="override",
        stage="pre_chunking",
        condition=_has_gpu,
        value_fn=_dynamic_batch_max,
        reason_fn=lambda m: (
            f"vram_total={m.vram_total_gb:.1f}GB -> dynamic batch ceiling "
            f"{_dynamic_batch_max(m)}"
        ),
    ),
    ProbeRule(
        key="performance.max_chunking_workers",
        kind="override",
        stage="pre_chunking",
        condition=lambda m: m.cpu_count >= 2 and m.file_count > 0,
        value_fn=_chunking_workers,
        reason_fn=lambda m: (
            f"cpu_count={m.cpu_count}, files={m.file_count} -> "
            f"{_chunking_workers(m)} (effective on next reindex)"
        ),
    ),
    ProbeRule(
        key="reranker.enabled",
        kind="override",
        stage="pre_chunking",
        condition=_reranker_below_floor,
        value_fn=lambda m: False,
        reason_fn=_reranker_below_floor_reason,
    ),
    ProbeRule(
        key="reranker.batch_size",
        kind="override",
        stage="pre_chunking",
        condition=lambda m: (
            _reranker_squeezed(m)
            or (m.vram_total_gb is not None and m.vram_total_gb >= 18)
        ),
        value_fn=lambda m: 8 if _reranker_squeezed(m) else 32,
        reason_fn=lambda m: (
            f"vram_total={m.vram_total_gb:.1f}GB -> reranker batch "
            f"{8 if _reranker_squeezed(m) else 32} (applies to "
            "NeuralReranker/GenerativeReranker; ignored by jina-reranker-v3, "
            "the deployed default, which batches internally)"
        ),
    ),
    ProbeRule(
        key="performance.vram_limit_fraction",
        kind="override",
        stage="pre_chunking",
        condition=lambda m: m.vram_total_gb is not None and m.vram_total_gb < 6,
        value_fn=lambda m: 0.70,
        reason_fn=lambda m: (
            f"vram_total={m.vram_total_gb:.1f}GB -> cap at 70% to leave "
            "display/compositor headroom on small GPUs"
        ),
    ),
    ProbeRule(
        key="performance.prefer_bf16",
        kind="override",
        stage="pre_chunking",
        condition=lambda m: _has_gpu(m) and m.gpu_bf16_supported is False,
        value_fn=lambda m: False,
        reason_fn=lambda m: "GPU reports no native bf16 support -> prefer fp16",
    ),
    # --- Pass 1: corpus-structural override -----------------------------
    ProbeRule(
        key="chunking.glsl_filter_td_prefix",
        kind="override",
        stage="pre_chunking",
        condition=_glsl_present,
        value_fn=lambda m: True,
        reason_fn=lambda m: (
            f"{sum(c for e, c in m.language_histogram.items() if e in GLSL_EXTENSIONS)} "
            "GLSL files present -> pin TouchDesigner TD-prefix builtin filter "
            "(hand-disable for non-TouchDesigner GLSL projects)"
        ),
    ),
    # --- Pass 1: observations (report-only) -----------------------------
    ProbeRule(
        key="embedding.model_name",
        kind="observation",
        stage="pre_chunking",
        condition=_embedding_model_mismatch,
        value_fn=None,
        reason_fn=_embedding_model_reason,
    ),
    ProbeRule(
        key="chunking.max_split_chars",
        kind="observation",
        stage="pre_chunking",
        condition=lambda m: (
            m.repo_profile is not None and m.repo_profile.p90_chars > 3200
        ),  # 2x the 1600-char default
        value_fn=None,
        reason_fn=_max_split_chars_reason,
    ),
    # --- Pass 2: observations from persisted stats ----------------------
    ProbeRule(
        key="chunking.max_chunk_lines",
        kind="observation",
        stage="post_build",
        condition=lambda m: _stats_split_share(m) > 0.15,
        value_fn=None,
        reason_fn=lambda m: (
            f"{_stats_split_share(m):.0%} of chunks are split_block fragments — "
            "functions frequently exceed the chunk budget; consider reviewing "
            "max_split_chars/max_chunk_lines for this corpus"
        ),
    ),
    ProbeRule(
        key="ego_graph.max_neighbors_per_hop",
        kind="observation",
        stage="post_build",
        condition=lambda m: _stats_chunks_per_file(m) > 25,
        value_fn=None,
        reason_fn=lambda m: (
            f"{_stats_chunks_per_file(m):.1f} chunks/file on average — dense "
            "files can flood graph-expansion pools; keep ego-graph/multi-hop "
            "expansion conservative on this corpus"
        ),
    ),
)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


def _set_dotted(target: dict[str, Any], dotted_key: str, value: Any) -> None:
    """Set ``{"a": {"b": value}}`` for dotted key ``"a.b"`` in-place."""
    parts = dotted_key.split(".")
    node = target
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def run_rules(
    measurements: ProbeMeasurements,
    stage: Literal["pre_chunking", "post_build"],
    rules: tuple[ProbeRule, ...] = RULES,
) -> ProbeResult:
    """Evaluate all rules for *stage* against *measurements*.

    A rule that raises is skipped with a warning — the probe must never break
    indexing.
    """
    result = ProbeResult()
    for rule in rules:
        if rule.stage != stage:
            continue
        try:
            if not rule.condition(measurements):
                continue
            if rule.kind == "override":
                assert rule.value_fn is not None  # override rules always carry one
                _set_dotted(result.overrides, rule.key, rule.value_fn(measurements))
                result.reasons[rule.key] = rule.reason_fn(measurements)
            else:
                result.observations.append(
                    {"key": rule.key, "note": rule.reason_fn(measurements)}
                )
        except Exception as e:  # noqa: BLE001 - probe isolation: one bad rule must not break indexing
            logger.warning(f"[INDEX_PROBE] Rule '{rule.key}' failed, skipped: {e}")
    return result


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def write_overrides_file(
    project_dir: Path | str,
    result: ProbeResult,
    mode: Literal["create", "append"] = "create",
) -> Path:
    """Persist a probe result to ``<project_dir>/search_overrides.json``.

    ``mode="create"`` overwrites wholesale (fresh provenance — stale reasons
    must not linger).  ``mode="append"`` extends the existing file's
    ``observations`` list (deduplicated), preserving pass-1 overrides/reasons
    and ``generated_at``; a missing or malformed existing file degrades to a
    fresh create.
    """
    path = Path(project_dir) / PROJECT_OVERRIDES_FILENAME
    payload: dict[str, Any] | None = None

    if mode == "append" and path.exists():
        try:
            with open(path) as f:
                existing = json.load(f)
            if not isinstance(existing, dict):
                raise TypeError("overrides file root must be a JSON object")
            seen = {
                (o.get("key"), o.get("note"))
                for o in existing.get("observations") or []
                if isinstance(o, dict)
            }
            merged = list(existing.get("observations") or [])
            merged.extend(
                o for o in result.observations if (o["key"], o["note"]) not in seen
            )
            existing["observations"] = merged
            payload = existing
        except (OSError, ValueError, TypeError) as e:
            logger.warning(
                f"[INDEX_PROBE] Could not append to {path} ({e}); rewriting fresh"
            )

    if payload is None:
        payload = {
            "probe_version": PROBE_VERSION,
            "generated_at": _utc_now_iso(),
            "overrides": result.overrides,
            "reasons": result.reasons,
            "observations": result.observations,
        }

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    return path


# ---------------------------------------------------------------------------
# Measurement + entry points
# ---------------------------------------------------------------------------


def _measure_gpu() -> tuple[float | None, float | None, bool | None]:
    """Return (vram_total_gb, vram_free_gb, bf16_supported); Nones without CUDA."""
    try:
        import torch

        if not torch.cuda.is_available():
            return None, None, None
        free_b, total_b = torch.cuda.mem_get_info(0)
        return (
            total_b / (1024**3),
            free_b / (1024**3),
            bool(torch.cuda.is_bf16_supported()),
        )
    except ImportError:
        return None, None, None
    except (RuntimeError, AssertionError, AttributeError) as e:
        logger.warning(f"[INDEX_PROBE] GPU measurement failed: {e}")
        return None, None, None


def _language_histogram(supported_files: list[str]) -> dict[str, int]:
    histogram: dict[str, int] = {}
    for file_path in supported_files:
        ext = Path(file_path).suffix.lower()
        if ext:
            histogram[ext] = histogram.get(ext, 0) + 1
    return histogram


def _probe_enabled() -> bool:
    """Both escape hatches silence the probe (matching the read-side gating)."""
    env_disable = os.environ.get("CLAUDE_DISABLE_PROJECT_OVERRIDES", "")
    if env_disable.strip().lower() in ("true", "1", "yes", "on", "enabled"):
        return False
    return get_search_config().performance.enable_project_overrides


def probe_pre_chunking(
    project_dir: Path | str,
    supported_files: list[str],
    repo_profile: RepoProfile | None,
    embedding_model: str | None = None,
    measurements: ProbeMeasurements | None = None,
) -> dict[str, Any] | None:
    """Pass 1: measure hardware + corpus shape, write overrides wholesale.

    Called from ``IncrementalIndexer._full_index`` after repo profiling and
    before chunking, so the freshly written file is already merged into the
    pipeline's next ``get_search_config()`` call.  Returns a compact summary
    dict, or ``None`` when the probe is disabled.
    """
    if not _probe_enabled():
        logger.debug("[INDEX_PROBE] Disabled via escape hatch, skipping pass 1")
        return None

    if measurements is None:
        vram_total, vram_free, bf16 = _measure_gpu()
        measurements = ProbeMeasurements(
            vram_total_gb=vram_total,
            vram_free_gb=vram_free,
            gpu_bf16_supported=bf16,
            cpu_count=os.cpu_count() or 1,
            file_count=len(supported_files),
            language_histogram=_language_histogram(supported_files),
            repo_profile=repo_profile,
            embedding_model=embedding_model,
        )

    result = run_rules(measurements, "pre_chunking")
    path = write_overrides_file(project_dir, result, mode="create")
    summary = result.summary("pre_chunking")
    logger.info(
        f"[INDEX_PROBE] Pass 1 wrote {len(result.reasons)} overrides, "
        f"{len(result.observations)} observations -> {path}"
    )
    return summary


def probe_post_build(
    project_dir: Path | str,
    stats: dict[str, Any],
    measurements: ProbeMeasurements | None = None,
) -> dict[str, Any] | None:
    """Pass 2: append report-only observations derived from persisted stats.

    Called from the index handler after a successful full-index write.  Reads
    only already-persisted data (``stats.json``) — no fresh graph analysis.
    Returns a compact summary dict, or ``None`` when disabled or nothing new.
    """
    if not _probe_enabled():
        logger.debug("[INDEX_PROBE] Disabled via escape hatch, skipping pass 2")
        return None

    if measurements is None:
        measurements = ProbeMeasurements(
            vram_total_gb=None,
            vram_free_gb=None,
            gpu_bf16_supported=None,
            cpu_count=os.cpu_count() or 1,
            file_count=int(stats.get("files_indexed", 0) or 0),
            language_histogram={},
            repo_profile=None,
            stats=stats,
        )

    result = run_rules(measurements, "post_build")
    if not result.observations:
        return None
    path = write_overrides_file(project_dir, result, mode="append")
    summary = result.summary("post_build")
    logger.info(
        f"[INDEX_PROBE] Pass 2 appended {len(result.observations)} "
        f"observations -> {path}"
    )
    return summary


def merged_probe_summary(
    pass1: dict[str, Any] | None, pass2: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Fold both pass summaries into one dict for the MCP index response."""
    if not pass1 and not pass2:
        return None
    merged: dict[str, Any] = {
        "probe_version": PROBE_VERSION,
        "override_keys": [],
        "reasons": {},
        "observation_keys": [],
    }
    for part in (pass1, pass2):
        if not part:
            continue
        merged["override_keys"].extend(part.get("override_keys", []))
        merged["reasons"].update(part.get("reasons", {}))
        merged["observation_keys"].extend(part.get("observation_keys", []))
    return merged


__all__ = [
    "FORBIDDEN_AUTO_TUNE_KEYS",
    "GLSL_EXTENSIONS",
    "PROBE_VERSION",
    "RULES",
    "ProbeMeasurements",
    "ProbeResult",
    "ProbeRule",
    "merged_probe_summary",
    "probe_post_build",
    "probe_pre_chunking",
    "run_rules",
    "write_overrides_file",
]
