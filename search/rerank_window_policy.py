"""Rerank window policy — which of the two rerank passes is running.

See CONTEXT.md's "Rerank window" / "Rerank pass" glossary entries. The one field
here is a named encoding of one fact: whether this
`RerankingEngine.rerank_by_query` call is the tail pass (after ego-graph/
parent-expansion, real scores, plain score order) or MultiHopSearcher's Pass-2
over the merged pool, whose window membership is decided by interleaving hop-1
survivors with the expansion frontier (ADR-0079).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RerankWindowPolicy:
    """How the rerank window is composed before the listwise pass."""

    interleave: bool = False

    @classmethod
    def tail(cls) -> "RerankWindowPolicy":
        """The post-expansion pass: plain score order, real scores."""
        return cls()

    @classmethod
    def merged_pool(cls) -> "RerankWindowPolicy":
        """Multi-hop Pass-2: window membership by hop-1/frontier interleave."""
        return cls(interleave=True)
