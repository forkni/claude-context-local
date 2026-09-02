"""Rerank window policy — which of the two rerank passes is running.

See CONTEXT.md's "Rerank window" / "Rerank pass" glossary entries. The four
fields here are a named encoding of one fact: whether this
`RerankingEngine.rerank_by_query` call is the tail pass (after ego-graph/
parent-expansion, real scores, no reserve) or MultiHopSearcher's Pass-2 over
the merged pool (three knobs read off `SearchConfig.reranker`, plus
`graph_hop_unscored` derived from `SearchConfig.graph_enhanced`'s ADR-0039
gate).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:  # pragma: no mutate
    from .config import SearchConfig


@dataclass(frozen=True)
class RerankWindowPolicy:
    """How the rerank window is composed before the listwise pass."""

    hop1_reserved_slots: int = 0
    merged_pool_policy: str = "score"
    graph_hop_window_cap: int = 0
    graph_hop_unscored: bool = False

    @classmethod
    def tail(cls) -> "RerankWindowPolicy":
        """The post-expansion pass: no reserve, plain score order, real scores."""
        return cls()

    @classmethod
    def merged_pool(cls, config: "SearchConfig") -> "RerankWindowPolicy":
        """Multi-hop Pass-2: reads the four knobs, incl. the ADR-0039 gate.

        `graph_hop_unscored` is derived here from the same gate
        `MultiHopSearcher._graph_expand` reads to decide whether to write a
        real anchor-conditioned score onto `graph_hop` candidates: unscored
        (the ADR-0039 placeholder) unless A1 call-evidence scoring is on.
        """
        ge_cfg = getattr(config, "graph_enhanced", None)
        graph_hop_unscored = not (
            ge_cfg is not None and ge_cfg.graph_hop_call_evidence_enabled
        )
        return cls(
            hop1_reserved_slots=config.reranker.hop1_reserved_slots,
            merged_pool_policy=config.reranker.merged_pool_policy,
            graph_hop_window_cap=config.reranker.graph_hop_window_cap,
            graph_hop_unscored=graph_hop_unscored,
        )
