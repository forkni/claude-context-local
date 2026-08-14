"""Config field liveness ratchet (ADR-0022).

Freezes ADR-0020's manually-verified liveness result rather than reproducing
it - that audit verified each field with three independent methods (semantic
search, find_connections zero-caller confirmation, exhaustive grep) agreeing
before pronouncing a field dead. A name-match cannot stand in for that: bare
field-name matching finds a "hit" for every one of the 124 fields, including
all 13 fields ADR-0020 proved dead, so it is not an audit.

What this test *does* catch: the declared reader file being deleted or
renamed, and a field surviving the removal of the code that consumed it -
exactly the drift that accumulated ADR-0020's 13 dead fields between audits.
"""

import dataclasses
from pathlib import Path

from search.config import SearchConfig


REPO_ROOT = Path(__file__).resolve().parents[3]


def _iter_fields():
    for _section_name, section_cls in SearchConfig._SUBCONFIG_TYPES.items():
        for f in dataclasses.fields(section_cls):
            yield section_cls.__name__, f


def test_every_field_declares_reader_or_is_schema_only():
    """Each field must opt into liveness tracking via reader=, or explicitly
    opt out via schema_only=True - there is no silent third option."""
    missing = [
        f"{cls_name}.{f.name}"
        for cls_name, f in _iter_fields()
        if not f.metadata.get("schema_only") and f.metadata.get("reader") is None
    ]
    assert not missing, (
        "Field(s) with neither spec(reader=...) nor spec(schema_only=True) "
        "(see ADR-0022): " + ", ".join(missing)
    )


def test_reader_files_exist():
    missing_files = [
        f"{cls_name}.{f.name} -> {reader}"
        for cls_name, f in _iter_fields()
        if (reader := f.metadata.get("reader")) is not None
        and not (REPO_ROOT / reader).exists()
    ]
    assert not missing_files, (
        "Declared reader file(s) do not exist (renamed/deleted?):\n  "
        + "\n  ".join(missing_files)
    )


def test_reader_files_mention_field_name():
    missing_mentions = []
    for cls_name, f in _iter_fields():
        reader = f.metadata.get("reader")
        if reader is None:
            continue
        text = (REPO_ROOT / reader).read_text(encoding="utf-8")
        if f.name not in text:
            missing_mentions.append(f"{cls_name}.{f.name} -> {reader}")
    assert not missing_mentions, (
        "Field name not found anywhere in its declared reader file (field "
        "may no longer be live - see ADR-0020/ADR-0022):\n  "
        + "\n  ".join(missing_mentions)
    )


def test_construction_baked_fields_are_pinned():
    """Ratchet for spec(construction_baked=True) (Part 2/C1 of the ADR-0018
    follow-on plan): the thirteen fields read once into a collaborator (cached
    HybridSearcher/reranker) at construction rather than live per search call
    - pin the exact set so a silent addition or removal shows up here instead
    of only as a stale benchmark arm that silently didn't take effect.

    reranker.batch_size and reranker.instruction were added by the 2026-08-06
    config-liveness audit: both are read in the same create_reranker(...) call
    as doc_max_chars/listwise_doc_max_chars/listwise_dtype (already pinned
    below) but had been left untagged, so requires_rebuild() returned False
    for an arm overriding either - it silently measured the un-overridden
    value. batch_size also carries mcp="reranker_echo" (read-only echo, not
    settable via MCP), which is why the sibling test below narrows to
    settable mcp tags instead of forbidding construction_baked+mcp outright.

    search_mode.bm25_weight/dense_weight were removed from this set (Phase 2a,
    ADR-0018 follow-on): HybridSearcher.__init__ takes no weight parameters -
    both are read live from effective_config on every search() call
    (hybrid_searcher.py:731-739), so the original six-field set (identified by
    hand from run_sscg_benchmark.py's _maybe_reset_for_construction_overrides)
    was wrong about those two. See test_weight_change_takes_effect_without_rebuild
    for the direct liveness proof.

    The six search_mode.bm25_*/performance.max_parallel_workers fields were
    added by the C3+C4 config-seam deepening (ADR-0030): all six were passed
    as primitive kwargs to HybridSearcher.__init__ (read once there, several
    only at BM25Index build/load/rebuild) but had never been marked
    construction_baked=True, so a benchmark arm overriding e.g.
    search_mode.bm25_k1 silently measured the pre-override value - the same
    failure class this ratchet exists to catch. See
    test_requires_rebuild_true_for_construction_baked_fields in
    tests/unit/evaluation/test_arm_overrides.py for the direct proof.
    """
    expected = frozenset(
        {
            ("search_mode", "rrf_k_parameter"),
            ("search_mode", "bm25_k1"),
            ("search_mode", "bm25_b"),
            ("search_mode", "bm25_use_stopwords"),
            ("search_mode", "bm25_use_stemming"),
            ("search_mode", "bm25_tokenizer"),
            ("performance", "max_parallel_workers"),
            ("reranker", "doc_max_chars"),
            ("reranker", "listwise_doc_max_chars"),
            ("reranker", "listwise_dtype"),
            ("reranker", "batch_size"),
            ("reranker", "instruction"),
            # A4 pilot (2026-08-14): read in the same create_reranker(...) call
            # as the five reranker fields above - captured on the instance at
            # construction, so an arm override needs a rebuild to take effect.
            ("reranker", "doc_representation_mode"),
        }
    )
    assert expected == SearchConfig._CONSTRUCTION_BAKED_FIELDS


def test_construction_baked_fields_declare_a_reader():
    """A construction_baked field with no reader would make requires_rebuild()
    correct but unverifiable - reader= is what test_reader_files_mention_field_name
    checks stays truthful, so construction_baked riding along on schema_only
    would silently escape that check."""
    unreadered = [
        f"{cls_name}.{f.name}"
        for cls_name, f in _iter_fields()
        if f.metadata.get("construction_baked") and f.metadata.get("reader") is None
    ]
    assert not unreadered, (
        "construction_baked=True field(s) with no reader=...:\n  "
        + "\n  ".join(unreadered)
    )


def test_no_mcp_settable_field_is_construction_baked():
    """Ratchet: spec(mcp=...) and spec(construction_baked=True) must never be
    set together for a *settable* mcp tag (see ADR-0027/mcp-field-derivation).

    A field tagged mcp="<section>" is patched live onto the cached SearchConfig
    by an MCP handler (see apply_config_patch); a field tagged
    construction_baked=True is read once into a collaborator (cached
    HybridSearcher/reranker) at construction, so mutating it on the config
    singleton is a no-op until that collaborator is rebuilt. A field carrying
    both tags would silently accept an MCP-set value that never takes effect -
    the handler must call state.reset_searcher() (dropping construction_baked),
    or the field must not be MCP-settable (dropping mcp=).

    mcp="<section>_echo" is a different tag: it marks a field that is
    read-only-echoed back after a patch (see config_handlers.py's
    _RERANKER_ECHO) but is never itself settable via MCP - _RERANKER_FIELDS
    derives only from non-echo tags, so an echo-tagged field can carry
    construction_baked=True with no MCP-liveness hazard (reranker.batch_size
    is exactly this case). Only settable tags are checked here.
    """
    exposed = [
        f"{cls_name}.{f.name}"
        for cls_name, f in _iter_fields()
        if f.metadata.get("mcp")
        and not f.metadata.get("mcp").endswith("_echo")
        and f.metadata.get("construction_baked")
    ]
    assert not exposed, (
        "MCP-settable field(s) baked at construction - the handler must call "
        "state.reset_searcher(), or drop the mcp= tag:\n  " + "\n  ".join(exposed)
    )
