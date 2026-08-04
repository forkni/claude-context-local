"""Unit tests for search/query_expansion.py (curated-vocabulary matcher)."""

import pytest

from search.query_expansion import (
    _load_variants,
    build_variant_query,
    match_concepts,
)


@pytest.fixture(autouse=True)
def clear_variants_cache():
    """Isolate the module-level YAML cache between tests."""
    _load_variants.cache_clear()
    yield
    _load_variants.cache_clear()


# ---------------------------------------------------------------------------
# Packaged default table
# ---------------------------------------------------------------------------


def test_default_table_loads_nonempty():
    """The packaged config/query_expansion_variants.yaml loads with concepts."""
    table = _load_variants("")
    assert len(table) >= 10
    for name, triggers, terms in table:
        assert name
        assert triggers, f"concept {name} has no triggers"
        assert terms, f"concept {name} has no terms"
        assert all(t == t.lower() for t in triggers), (
            f"concept {name} has non-lowercase triggers"
        )


def test_default_table_cap_respected():
    """Curation policy: the packaged table stays at ~15 concepts max."""
    assert len(_load_variants("")) <= 15


def test_match_is_case_insensitive():
    matches = match_concepts("How Does State SURVIVE A RESTART?")
    assert [name for name, _ in matches] == ["persistence"]


def test_no_match_returns_empty():
    assert match_concepts("where is QueryRouter defined") == []


def test_max_variants_caps_matches_in_file_order():
    """A query firing >max_variants concepts keeps the first N in file order."""
    # "persist ... evict ... cache" fires persistence, eviction, caching
    query = "persist the cache and evict old entries"
    two = match_concepts(query, max_variants=2)
    three = match_concepts(query, max_variants=3)
    assert len(two) == 2
    assert len(three) == 3
    assert [n for n, _ in three][:2] == [n for n, _ in two]


def test_max_variants_zero_returns_empty():
    assert match_concepts("persist this", max_variants=0) == []


def test_match_is_deterministic():
    query = "hold several loaded encoders when memory gets tight"
    assert match_concepts(query) == match_concepts(query)


def test_terms_are_returned_as_lists():
    matches = match_concepts("make room by discarding the stalest entries")
    assert matches
    name, terms = matches[0]
    assert name == "eviction"
    assert isinstance(terms, list)
    assert "evict" in terms


# ---------------------------------------------------------------------------
# Variant query construction
# ---------------------------------------------------------------------------


def test_build_variant_query_appends_terms():
    assert (
        build_variant_query("survive a restart", ["save", "disk"])
        == "survive a restart save disk"
    )


# ---------------------------------------------------------------------------
# Fail-open loading
# ---------------------------------------------------------------------------


def test_missing_file_yields_empty_table(tmp_path):
    assert _load_variants(str(tmp_path / "nope.yaml")) == ()
    assert match_concepts("persist this", str(tmp_path / "nope.yaml")) == []


def test_malformed_yaml_yields_empty_table(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("concepts: [unclosed", encoding="utf-8")
    assert _load_variants(str(bad)) == ()


def test_missing_concepts_key_yields_empty_table(tmp_path):
    bad = tmp_path / "no_key.yaml"
    bad.write_text("something_else: {}", encoding="utf-8")
    assert _load_variants(str(bad)) == ()


def test_concepts_missing_triggers_or_terms_are_dropped(tmp_path):
    partial = tmp_path / "partial.yaml"
    partial.write_text(
        "concepts:\n"
        "  no_terms:\n"
        "    triggers: ['foo']\n"
        "  no_triggers:\n"
        "    terms: ['bar']\n"
        "  complete:\n"
        "    triggers: ['baz']\n"
        "    terms: ['qux']\n",
        encoding="utf-8",
    )
    table = _load_variants(str(partial))
    assert [name for name, _, _ in table] == ["complete"]


def test_custom_table_matching(tmp_path):
    custom = tmp_path / "custom.yaml"
    custom.write_text(
        "concepts:\n"
        "  widgets:\n"
        "    triggers: ['widget']\n"
        "    terms: ['gadget', 'gizmo']\n",
        encoding="utf-8",
    )
    matches = match_concepts("find the widget factory", str(custom))
    assert matches == [("widgets", ["gadget", "gizmo"])]
