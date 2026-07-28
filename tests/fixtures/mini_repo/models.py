"""Domain model for the ``mini_repo`` fixture.

``mini_repo`` exists so ``tests/integration/test_call_edge_injection_integration.py``
can run the real indexing pipeline against files with genuine cross-module
calls — pyan3 and libcst need actual imports and call sites to resolve, and a
hand-built ``raw_line_map`` (the pattern used elsewhere for unit tests) does
not exercise the full ``IncrementalIndexer`` -> ``IndexWriteStage`` ->
``inject_call_edges`` path end to end.
"""


class Widget:
    """A simple domain object. ``repository.py`` calls its method across files."""

    def __init__(self, name: str, price: float) -> None:
        self.name = name
        self.price = price

    def get_display_name(self) -> str:
        """Return a human-readable label — called from ``repository.get_widget``."""
        return f"{self.name} (${self.price:.2f})"
