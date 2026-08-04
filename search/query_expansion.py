"""Curated-vocabulary query expansion (deterministic trigger matching).

Loads the concept table from ``config/query_expansion_variants.yaml`` and
matches queries against concept triggers via lowercase substring containment.
Matched concepts' terms become extra discounted fusion legs in the hybrid
search path (``SearchExecutor.execute_single_hop``) — see
``docs/adr/0006-curated-vocabulary-query-expansion.md`` for why a curated
table was chosen over PRF or an LLM rewrite hook.

Design constraints:
- No embeddings, no per-query I/O after the first load (module-level cache).
- Deterministic: concepts are evaluated in file order; ties never reorder.
- Fail-open: a missing or malformed YAML disables expansion with one warning
  (same recovery pattern as ``intent_classifier._load_anchor_config``).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path


logger = logging.getLogger(__name__)

_DEFAULT_VARIANTS_PATH = (
    Path(__file__).parent.parent / "config" / "query_expansion_variants.yaml"
)

# (concept_name, lowercased_triggers, terms) in file order
_ConceptTable = tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...]


@lru_cache(maxsize=4)
def _load_variants(path_str: str) -> _ConceptTable:
    """Load + normalize the concept table for *path_str* (cached per path).

    An empty *path_str* resolves to the packaged default YAML. Concepts with
    no triggers or no terms are dropped. Returns an empty table (expansion
    is a no-op) on any load/parse failure, logging one warning.

    Tests that patch the YAML on disk must call
    ``_load_variants.cache_clear()`` for the patch to take effect.
    """
    path = Path(path_str) if path_str else _DEFAULT_VARIANTS_PATH
    try:
        import yaml

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        concepts = data["concepts"]
        table = []
        for name, spec in concepts.items():
            triggers = tuple(str(t).lower() for t in (spec.get("triggers") or []) if t)
            terms = tuple(str(t) for t in (spec.get("terms") or []) if t)
            if triggers and terms:
                table.append((str(name), triggers, terms))
        return tuple(table)
    except Exception as exc:  # noqa: BLE001 - parse-recovery: malformed/missing variants YAML disables expansion
        logger.warning(f"[QUERY-EXPANSION] Failed to load {path}: {exc}")
        return ()


def match_concepts(
    query: str, variants_path: str = "", max_variants: int = 2
) -> list[tuple[str, list[str]]]:
    """Return up to *max_variants* ``(concept_name, terms)`` matches for *query*.

    A concept matches when any of its triggers appears as a substring of the
    lowercased query. Matches are returned in concept-table (file) order, so
    the result is deterministic for a given query + table.
    """
    if max_variants <= 0:
        return []
    lowered = query.lower()
    matches: list[tuple[str, list[str]]] = []
    for name, triggers, terms in _load_variants(variants_path):
        if any(trigger in lowered for trigger in triggers):
            matches.append((name, list(terms)))
            if len(matches) >= max_variants:
                break
    return matches


def build_variant_query(query: str, terms: list[str]) -> str:
    """Append a concept's expansion terms to the original query text."""
    return f"{query} {' '.join(terms)}"
