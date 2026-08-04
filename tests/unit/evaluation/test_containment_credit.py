"""Unit tests for containment-credit scoring in evaluation/metrics.py.

Merged chunks (chunk_type="merged") can never match golden IDs on the strict
``file:type:name`` dedup key (see evaluation/CHUNKING_MERGE_AB_20260728.md).
Containment credit widens each retrieved position to a set of IDs the chunk
may be credited as, driven by the persisted ``merged_from`` member list.

Covers: RetrievedEntry set handling in the four core metric functions
(including exact parity with plain-string scoring), flatten_entries,
build_merged_membership, _golden_id_matches_member, and
expand_retrieved_with_containment (incl. the Q40 wrong-representative-name
scenario and the merge-free no-op guarantee).
"""

import pytest

from evaluation.metrics import (
    _golden_id_matches_member,
    build_merged_membership,
    calculate_metrics_from_results,
    calculate_mrr,
    calculate_ndcg_at_k,
    calculate_precision_at_k,
    calculate_recall_at_k,
    expand_retrieved_with_containment,
    flatten_entries,
    normalize_chunk_ids,
)


GOLD_REMOVE = "merkle/change_detector.py:method:ChangeDetector.get_files_to_remove"
GOLD_REINDEX = "merkle/change_detector.py:method:ChangeDetector.get_files_to_reindex"


class FakeMetadataStore:
    """Minimal stand-in exposing MetadataStore.items() -> (raw_id, entry)."""

    def __init__(self, entries: dict[str, dict]):
        self._entries = entries

    def items(self):
        return self._entries.items()


# ---------------------------------------------------------------------------
# Set-entry handling in the core metric functions
# ---------------------------------------------------------------------------


class TestMetricFunctionsWithSetEntries:
    def test_mrr_credits_set_entry_at_rank_1(self):
        retrieved = [{"a.py:merged:X", GOLD_REMOVE}, "b.py:function:other"]
        assert calculate_mrr(retrieved, [GOLD_REMOVE]) == 1.0

    def test_mrr_set_entry_without_gold_scores_zero(self):
        retrieved = [{"a.py:merged:X", "a.py:function:unrelated"}]
        assert calculate_mrr(retrieved, [GOLD_REMOVE]) == 0.0

    def test_recall_counts_each_contained_gold(self):
        # One merged chunk absorbing both golds → full recall at k=1
        entry = {"a.py:merged:X", GOLD_REMOVE, GOLD_REINDEX}
        assert calculate_recall_at_k([entry], [GOLD_REMOVE, GOLD_REINDEX], 1) == 1.0

    def test_recall_does_not_double_count_across_ranks(self):
        retrieved = [{"a.py:merged:X", GOLD_REMOVE}, GOLD_REMOVE]
        assert calculate_recall_at_k(retrieved, [GOLD_REMOVE, GOLD_REINDEX], 5) == 0.5

    def test_precision_uses_matched_gold_count(self):
        entry = {"a.py:merged:X", GOLD_REMOVE, GOLD_REINDEX}
        result = calculate_precision_at_k(
            [entry, "b.py:function:noise"], [GOLD_REMOVE, GOLD_REINDEX], 2
        )
        assert result == 1.0  # 2 matched golds / k=2

    def test_ndcg_scores_set_entry_position(self):
        retrieved = ["b.py:function:noise", {"a.py:merged:X", GOLD_REMOVE}]
        with_set = calculate_ndcg_at_k(retrieved, [GOLD_REMOVE], 5)
        plain = calculate_ndcg_at_k(
            ["b.py:function:noise", GOLD_REMOVE], [GOLD_REMOVE], 5
        )
        assert with_set == pytest.approx(plain)

    def test_string_only_inputs_unchanged(self):
        # Backwards-compat parity: plain strings must score exactly as before
        retrieved = ["a.py:function:one", GOLD_REMOVE, "c.py:class:Three"]
        relevant = [GOLD_REMOVE, "c.py:class:Three"]
        assert calculate_mrr(retrieved, [GOLD_REMOVE]) == 0.5
        assert calculate_recall_at_k(retrieved, relevant, 3) == 1.0
        assert calculate_precision_at_k(retrieved, relevant, 3) == pytest.approx(2 / 3)
        assert calculate_ndcg_at_k(retrieved, relevant, 3) > 0.0

    def test_metrics_from_results_accepts_mixed_entries(self):
        retrieved = [{"a.py:merged:X", GOLD_REMOVE}, "b.py:function:noise"]
        metrics = calculate_metrics_from_results(
            retrieved=retrieved,
            expected=[GOLD_REMOVE],
            expected_primary=[GOLD_REMOVE],
        )
        assert metrics["mrr"] == 1.0
        assert metrics["recall@1"] == 1.0
        assert metrics["hit"] is True


class TestFlattenEntries:
    def test_mixed_entries(self):
        entries = ["a.py:function:one", {"m.py:merged:X", GOLD_REMOVE}]
        assert flatten_entries(entries) == {
            "a.py:function:one",
            "m.py:merged:X",
            GOLD_REMOVE,
        }

    def test_empty(self):
        assert flatten_entries([]) == set()


# ---------------------------------------------------------------------------
# build_merged_membership
# ---------------------------------------------------------------------------


class TestBuildMergedMembership:
    def test_only_merged_chunks_included(self):
        store = FakeMetadataStore(
            {
                "a.py:1-10:function:plain": {
                    "metadata": {"relative_path": "a.py", "name": "plain"}
                },
                "m.py:1-30:merged:Repr.first": {
                    "metadata": {
                        "relative_path": "m.py",
                        "merged_from": ["Repr.first", "Repr.second"],
                    }
                },
            }
        )
        membership = build_merged_membership(store)
        assert list(membership) == ["m.py:1-30:merged:Repr.first"]
        path, members = membership["m.py:1-30:merged:Repr.first"]
        assert path == "m.py"
        assert members == frozenset({"Repr.first", "Repr.second"})

    def test_backslash_paths_normalized(self):
        store = FakeMetadataStore(
            {
                "sub\\m.py:1-30:merged:f": {
                    "metadata": {
                        "relative_path": "sub\\m.py",
                        "merged_from": ["f", "g"],
                    }
                },
            }
        )
        (path, _members) = next(iter(build_merged_membership(store).values()))
        assert path == "sub/m.py"

    def test_merge_free_store_yields_empty(self):
        store = FakeMetadataStore(
            {
                "a.py:1-10:function:plain": {"metadata": {"relative_path": "a.py"}},
            }
        )
        assert build_merged_membership(store) == {}


# ---------------------------------------------------------------------------
# _golden_id_matches_member
# ---------------------------------------------------------------------------


class TestGoldenIdMatchesMember:
    MEMBERS = frozenset(
        {"ChangeDetector.get_files_to_reindex", "ChangeDetector.get_files_to_remove"}
    )

    def test_match(self):
        assert _golden_id_matches_member(
            GOLD_REMOVE, "merkle/change_detector.py", self.MEMBERS
        )

    def test_wrong_file(self):
        assert not _golden_id_matches_member(GOLD_REMOVE, "other/file.py", self.MEMBERS)

    def test_name_not_a_member(self):
        assert not _golden_id_matches_member(
            "merkle/change_detector.py:method:ChangeDetector.other",
            "merkle/change_detector.py",
            self.MEMBERS,
        )

    def test_nameless_module_id_never_matches(self):
        assert not _golden_id_matches_member(
            "merkle/change_detector.py:module",
            "merkle/change_detector.py",
            self.MEMBERS,
        )


# ---------------------------------------------------------------------------
# expand_retrieved_with_containment
# ---------------------------------------------------------------------------


class TestExpandRetrievedWithContainment:
    def test_empty_membership_equals_normalize_chunk_ids(self):
        raw = [
            "search/config.py:148-161:decorated_definition:EmbeddingConfig",
            "graph/g.py:276-310:split_block:GraphIntegration.populate",
            "search/config.py:148-161:decorated_definition:EmbeddingConfig",
        ]
        assert expand_retrieved_with_containment(raw, [GOLD_REMOVE], {}) == (
            normalize_chunk_ids(raw)
        )

    def test_q40_wrong_representative_name_gets_credit(self):
        # Q40: merged chunk named after get_files_to_reindex contains the
        # expected get_files_to_remove — name-based credit missed this;
        # merged_from membership must catch it.
        raw_id = (
            "merkle/change_detector.py:284-305:merged:"
            "ChangeDetector.get_files_to_reindex"
        )
        membership = {
            raw_id: (
                "merkle/change_detector.py",
                frozenset(
                    {
                        "ChangeDetector.get_files_to_reindex",
                        "ChangeDetector.get_files_to_remove",
                    }
                ),
            )
        }
        entries = expand_retrieved_with_containment([raw_id], [GOLD_REMOVE], membership)
        assert len(entries) == 1
        assert isinstance(entries[0], set)
        assert GOLD_REMOVE in entries[0]
        assert calculate_mrr(entries, [GOLD_REMOVE]) == 1.0

    def test_merged_chunk_without_contained_gold_stays_plain(self):
        raw_id = "a.py:1-30:merged:f"
        membership = {raw_id: ("a.py", frozenset({"f", "g"}))}
        entries = expand_retrieved_with_containment([raw_id], [GOLD_REMOVE], membership)
        assert entries == ["a.py:merged:f"]

    def test_dedup_by_normalized_own_id(self):
        raw = [
            "a.py:1-10:function:foo",
            "a.py:12-20:function:foo",  # same dedup key, dropped
        ]
        entries = expand_retrieved_with_containment(raw, [], {})
        assert entries == ["a.py:function:foo"]

    def test_one_merged_chunk_credits_multiple_golds(self):
        raw_id = "m.py:1-40:merged:A.first"
        golds = ["m.py:method:A.first", "m.py:method:A.second"]
        membership = {raw_id: ("m.py", frozenset({"A.first", "A.second"}))}
        entries = expand_retrieved_with_containment([raw_id], golds, membership)
        assert calculate_recall_at_k(entries, golds, 1) == 1.0
