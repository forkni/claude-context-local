"""Chunk sizing: how big is too big, and where to cut.

Owns the size arithmetic shared by function splitting and module-preamble
packing in ``chunking.languages.base.LanguageChunker``. Language-specific
parts (which nodes may be cut between, how a chunk is built) stay on the
chunker; this module only measures and packs.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any


logger = logging.getLogger(__name__)


def compute_adaptive_threshold(
    complexity: int,
    base_threshold: int,
    max_complexity: int = 30,
    multiplier_max: float = 1.3,
    multiplier_min: float = 0.5,
    hard_cap: int = 8000,
) -> int:
    """Compute complexity-modulated chunk size threshold.

    Implements the research formula for adaptive chunk sizing:
      Cv = min(complexity / max_complexity, 1.0)   # normalize: 0=linear, 1=max
      T(Cv) = T_max - (T_max - T_min) × Cv         # high CC → smaller chunks

    Args:
        complexity: Cyclomatic complexity of the function (raw integer, min 1)
        base_threshold: Project baseline (P75 of function sizes) in non-whitespace chars
        max_complexity: Normalization ceiling — CC >= this → Cv = 1.0 (default 30)
        multiplier_max: T_max = base_threshold × this (for low-complexity code, default 1.3)
        multiplier_min: T_min = base_threshold × this (for high-complexity code, default 0.5)
        hard_cap: Absolute ceiling in non-whitespace chars (~2500-token context cliff, default 8000)

    Returns:
        Effective max_chars threshold, always in range [T_min, hard_cap]

    Examples:
        >>> compute_adaptive_threshold(1, 3000)   # linear code: ~3900 chars
        3858
        >>> compute_adaptive_threshold(15, 3000)  # moderate: ~2700 chars
        2700
        >>> compute_adaptive_threshold(30, 3000)  # complex: 1500 chars
        1500
    """
    cv = min(complexity / max(max_complexity, 1), 1.0)
    t_max = base_threshold * multiplier_max
    t_min = base_threshold * multiplier_min
    effective = t_max - (t_max - t_min) * cv
    return min(int(effective), hard_cap)


def estimate_characters(content: str, count_whitespace: bool = False) -> int:
    """Count characters in content (cAST paper approach).

    Args:
        content: Text content to measure
        count_whitespace: If False, count non-whitespace only (cAST default)

    Returns:
        Character count

    Reference:
        cAST (EMNLP 2025): Uses non-whitespace characters for language-agnostic sizing
    """
    if count_whitespace:
        return len(content)
    # C-level non-whitespace count: str.split() drops runs of (Unicode) whitespace,
    # so joining the pieces back together and measuring their length avoids a
    # per-character Python-level generator. Parity with str.isspace() is exact in
    # CPython (both use the same Unicode whitespace definition).
    return len("".join(content.split()))


def measure(nodes: list[Any], source_bytes: bytes, unit: str) -> int:
    """Accumulated size of a run of sibling AST nodes.

    Args:
        nodes: Tree-sitter nodes in source order (the span first->last is measured).
        source_bytes: Source code bytes.
        unit: "lines" or "characters"; any other value falls back to lines.

    Returns:
        The size of the span from the first node's start to the last node's end.
    """
    if not nodes:
        return 0

    # Get text span from first to last node
    start = nodes[0].start_byte
    end = nodes[-1].end_byte
    text = source_bytes[start:end].decode("utf-8", errors="ignore")

    if unit == "lines":
        return text.count("\n") + 1
    elif unit == "characters":
        return estimate_characters(text)
    return text.count("\n") + 1  # default fallback


def pack_by_size(
    nodes: list[Any],
    source_bytes: bytes,
    threshold: int,
    unit: str,
    may_cut_before: Callable[[Any, Any], bool],
) -> list[list[Any]]:
    """Greedily pack sibling nodes into size-bounded groups.

    Accumulates `nodes` in order, cutting before a node only where
    `may_cut_before(current_group[-1], node)` allows a cut AND adding
    the node would bring the accumulated size to `threshold` or beyond.
    A cut never splits a single oversized node -- it always starts a
    new group with that node instead.

    Args:
        nodes: Sibling tree-sitter nodes to pack, in source order.
        source_bytes: Source code bytes.
        threshold: Size at which a group is closed.
        unit: "lines" or "characters", passed to `measure`.
        may_cut_before: Predicate(prev_node, node) -- whether a cut is
            allowed immediately before `node`, given the last node
            accumulated so far.

    Returns:
        List of non-empty node groups covering `nodes` in order.
    """
    groups: list[list[Any]] = []
    current_nodes: list[Any] = []

    for node in nodes:
        if current_nodes and may_cut_before(current_nodes[-1], node):
            test_nodes = current_nodes + [node]
            test_size = measure(test_nodes, source_bytes, unit)
            if test_size >= threshold:
                groups.append(current_nodes)
                current_nodes = [node]
                continue

        current_nodes.append(node)

    if current_nodes:
        groups.append(current_nodes)

    return groups
