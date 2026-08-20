"""Wire-interface specs for request-scoped result enrichers.

One ``EnricherSpec`` row is the single declaration of an opt-in ``search_code``
display parameter. Three modules derive from it instead of hand-typing their
own copy:

- ``mcp_server/config_schema.py`` — the ``HAND_TYPED`` default entry
  (``arg()``'s fallback and the published schema ``default``, ADR-0046).
- ``mcp_server/tool_specs.py`` — the published boolean schema property,
  including its description, on the ``search_code`` row's ``input_schema``.
- ``mcp_server/tools/search_orchestrator.py`` — the ``SearchPlan.display_params``
  read in ``SearchPlanner.plan()`` and the enrichment gate row.

The *application* side stays in ``mcp_server/tools/result_view.py``:
``RESULT_ENRICHERS`` owns each enricher's output field and apply function,
joined to these rows on ``key`` (drift-tested in
``tests/unit/mcp_server/test_search_orchestrator.py``). The ``graph`` enricher
has no row here — its gate is config-scoped (``OutputConfig
.include_result_graph``), not a wire parameter.

Adding a request-scoped enricher is therefore: one row here, plus the apply
function and its ``RESULT_ENRICHERS`` row — no schema, defaults-table, plan,
or gate edits.

This module is a leaf: stdlib imports only, so ``config_schema`` can depend on
it without touching ``mcp_server.tools``.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EnricherSpec:
    """The wire interface of one request-scoped enricher.

    key: gate key; joins to ``ResultEnricher.key`` in ``RESULT_ENRICHERS``.
    param: the ``search_code`` argument name.
    default: published schema default and the planner's ``arg()`` fallback.
    description: published schema description, verbatim.
    rationale: why no config field backs the default (``HandTyped.rationale``).
    """

    key: str
    param: str
    default: bool
    description: str
    rationale: str


ENRICHER_SPECS: tuple[EnricherSpec, ...] = (
    EnricherSpec(
        key="top_callers",
        param="include_top_callers",
        default=False,
        description=(
            "Attach up to 2 top callers per result as top_callers: "
            "[{name, file}] (default: False). Callers come from the code "
            "graph's incoming call edges — context agents cannot derive from "
            "the result text alone. Ordering prefers resolver-confident edges "
            "when available; otherwise discovery order (hint, not a guarantee)."
        ),
        rationale=(
            "request-scoped display opt-in — no config field; the planner "
            "falls back to this row's default via arg()"
        ),
    ),
    EnricherSpec(
        key="signatures",
        param="include_signatures",
        default=False,
        description=(
            "Attach a signature-only view per result as signature: str "
            "(default: False). search_code returns coordinates only "
            "(file/lines/kind/score) — no chunk content; this is a "
            "display-only counterfactual to a follow-up Read, not chunk "
            "content itself. Measured ~687 tokens/query overhead (~36% over "
            "the default compact format's payload size) — a hint, not a "
            "guarantee: module/module_preamble chunks are skipped (no "
            "callable contract to summarize); on non-Python chunks (no "
            "def/class anchor recognized) it degrades to the first 3 raw "
            "lines, capped at 600 characters. Never touches scoring, "
            "ordering, or the reranker."
        ),
        rationale=(
            "request-scoped display opt-in — no config field; the planner "
            "falls back to this row's default via arg()"
        ),
    ),
)
"""Rows in published-schema property order (also gate/application order
relative to each other; ``graph`` precedes both in ``RESULT_ENRICHERS``)."""
