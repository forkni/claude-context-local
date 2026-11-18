"""Pins for mutants that survived the 2026-11-18 cosmic-ray run on evaluation/metrics.py.

Each survivor was first replayed against every test file that imports the module
(tests/TESTING_GUIDE.md, Phase 18.3); these tests cover what was still alive. Expected
values are worked by hand from the function docstrings. The comment on each test names the
mutant(s) it kills (line numbers as of 2026-11-18).
"""

import pytest

from evaluation.metrics import (
    aggregate_metrics,
    build_community_membership,
    calculate_graded_ndcg_at_k,
    calculate_hard_negative_intrusion,
    calculate_metrics_from_results,
    expand_retrieved_with_community_credit,
    expand_retrieved_with_containment,
)


RANKED = [f"f.py:function:r{i}" for i in range(1, 13)]  # r1 .. r12, rank = suffix


def _at(rank: int) -> str:
    return RANKED[rank - 1]


# ── Graded NDCG ───────────────────────────────────────────────────────────────


def test_graded_ndcg_gives_an_empty_entry_zero_gain():
    # An empty containment set at rank 1, the grade-3 answer at rank 2:
    # dcg = 7 / log2(3), idcg = 7, so ndcg = 1 / log2(3). Kills L229 `default=0` -> 1 / -1.
    ndcg = calculate_graded_ndcg_at_k([set(), "a"], {"a": 3}, k=2)
    assert ndcg == pytest.approx(0.6309297535714575)


def test_graded_ndcg_ideal_ranking_counts_grade_one_ids():
    # The ideal list holds every positive grade (3 then 1), so this ranking is ideal
    # and scores exactly 1.0. Kills L237 `g > 0` -> `g > 1` (ndcg would exceed 1).
    assert calculate_graded_ndcg_at_k(["b", "a"], {"a": 1, "b": 3}, k=2) == 1.0


# ── Hard-negative intrusion ───────────────────────────────────────────────────


def test_a_tie_at_one_rank_is_not_an_intrusion():
    # One containment entry holds both the positive and the hard negative: the negative
    # did not rank strictly before the positive. Kills L314 `<` -> `<=`.
    assert calculate_hard_negative_intrusion([{"p", "n"}], ["p"], ["n"]) is False


@pytest.mark.parametrize(
    ("negative_rank", "positive_rank", "expected"),
    [(1, 10, True), (10, 11, None)],
    ids=["positive-at-the-default-cutoff", "positive-just-past-it"],
)
def test_intrusion_default_cutoff_is_ten(negative_rank, positive_rank, expected):
    # Kills L277 default `k=10` -> 9 (first case gives None) and -> 11 (second gives True).
    retrieved = list(RANKED)
    retrieved[negative_rank - 1] = "neg"
    retrieved[positive_rank - 1] = "pos"
    assert calculate_hard_negative_intrusion(retrieved, ["pos"], ["neg"]) is expected


# ── calculate_metrics_from_results: the k values behind each key ─────────────


@pytest.mark.parametrize(
    ("rank", "acc5", "acc10"),
    [(5, 1.0, 1.0), (6, 0.0, 1.0), (10, 0.0, 1.0), (11, 0.0, 0.0)],
    ids=["rank-5", "rank-6", "rank-10", "rank-11"],
)
def test_acc_keys_use_cutoffs_five_and_ten(rank, acc5, acc10):
    # Kills L380 / L381 `5` -> 4 / 6 and `10` -> 9 / 11.
    m = calculate_metrics_from_results(RANKED, [_at(rank)])
    assert (m["acc@5"], m["acc@10"]) == (acc5, acc10)


@pytest.mark.parametrize(
    ("rank", "graded5_positive", "graded10_positive"),
    [(5, True, True), (6, False, True), (10, False, True), (11, False, False)],
    ids=["rank-5", "rank-6", "rank-10", "rank-11"],
)
def test_graded_ndcg_keys_use_cutoffs_five_and_ten(
    rank, graded5_positive, graded10_positive
):
    # Kills L387 / L390 `5` -> 4 / 6 and `10` -> 9 / 11.
    m = calculate_metrics_from_results(
        RANKED, [_at(rank)], relevance_grades={_at(rank): 3}
    )
    assert (m["ndcg@5_graded"] > 0, m["ndcg@10_graded"] > 0) == (
        graded5_positive,
        graded10_positive,
    )


def test_grade_zero_ids_are_not_hard_negatives():
    # A grade-0 id ranked first is irrelevant, not a hard negative, so no hard negative
    # surfaced and intrusion is None. Kills L393 `grade == 1` -> `grade <= 1`.
    grades = {_at(1): 0, _at(2): 3}
    m = calculate_metrics_from_results(RANKED, [_at(2)], relevance_grades=grades)
    assert m["hard_negative_intrusion"] is None


@pytest.mark.parametrize(
    ("negative_rank", "positive_rank", "expected"),
    [(1, 10, True), (10, 11, None)],
    ids=["positive-at-ten", "positive-at-eleven"],
)
def test_metrics_intrusion_uses_cutoff_ten(negative_rank, positive_rank, expected):
    # Kills L396 `k=10` -> 9 / 11.
    grades = {_at(negative_rank): 1, _at(positive_rank): 3}
    m = calculate_metrics_from_results(
        RANKED, [_at(positive_rank)], relevance_grades=grades
    )
    assert m["hard_negative_intrusion"] is expected


# ── aggregate_metrics: presence-based rates ───────────────────────────────────


def test_aggregate_pool_window_and_intrusion_rates():
    # 2 of 3 true for each flag: rate 0.6667 (an inverted flag would give 0.3333).
    # pool_size missing in one row counts as 0: (12 + 6 + 0) / 3 = 6.0.
    # Kills L508 (AddNot and the four constant swaps), L512 default 0 -> 1 / -1,
    # L523 AddNot and L544 AddNot.
    rows = [
        {"pool_hit": True, "pool_size": 12, "gold_in_window": True,
         "hard_negative_intrusion": True},
        {"pool_hit": True, "pool_size": 6, "gold_in_window": True,
         "hard_negative_intrusion": True},
        {"pool_hit": False, "gold_in_window": False, "hard_negative_intrusion": False},
    ]  # fmt: skip
    agg = aggregate_metrics(rows)
    assert agg["pool_hit_rate"] == pytest.approx(0.6667)
    assert agg["avg_pool_size"] == 6.0
    assert agg["gold_in_window_rate"] == pytest.approx(0.6667)
    assert agg["hard_negative_intrusion_rate"] == pytest.approx(0.6667)


# ── Containment credit ────────────────────────────────────────────────────────


def test_containment_credits_only_members_of_the_same_file():
    # The merged chunk lives in a.py; a golden id in b.py with the same symbol name is
    # not absorbed. Kills L861 `path == ...` -> `>=` ("b.py" >= "a.py").
    membership = {"a.py:1-9:function:f": ("a.py", frozenset({"f"}))}
    out = expand_retrieved_with_containment(
        ["a.py:1-9:function:f"], ["b.py:function:f"], membership
    )
    assert out == ["a.py:function:f"]


def test_a_nameless_golden_id_is_never_a_member():
    # "f.py:module" has no symbol name, even when a member happens to be called "module".
    # Kills L859 `len(parts) < 3` -> `< 2` and -> `> 3`.
    membership = {"f.py:1-9:function:g": ("f.py", frozenset({"g", "module"}))}
    out = expand_retrieved_with_containment(
        ["f.py:1-9:function:g"], ["f.py:module"], membership
    )
    assert out == ["f.py:function:g"]


def test_containment_keeps_going_after_a_duplicate():
    # The second id normalizes to the first (different line range) and is dropped; the
    # third must still be processed. Kills L894 `continue` -> `break`.
    out = expand_retrieved_with_containment(
        ["f.py:1-9:function:f", "f.py:20-30:function:f", "g.py:1-2:function:g"], [], {}
    )
    assert out == ["f.py:function:f", "g.py:function:g"]


def test_containment_keeps_the_chunks_own_id_when_it_is_also_a_gold():
    # The merged chunk is itself a golden id and absorbed another gold: the entry holds
    # both. Kills L902 `{normalized} | contained` -> `^` (would drop its own id).
    membership = {"f.py:1-9:function:f": ("f.py", frozenset({"f", "g"}))}
    golds = ["f.py:function:f", "f.py:function:g"]
    out = expand_retrieved_with_containment(["f.py:1-9:function:f"], golds, membership)
    assert out == [{"f.py:function:f", "f.py:function:g"}]


# ── Community credit ──────────────────────────────────────────────────────────


def test_community_membership_skips_short_ids_and_keeps_going():
    # A nameless id first, then a named one: the named one must still be collected.
    # Kills L1043 `continue` -> `break`.
    membership = build_community_membership(
        {"f.py:1-8:module": 1, "g.py:1-2:function:g": 1}
    )
    assert membership == {1: frozenset({("g.py", "g")})}


def test_community_membership_needs_both_a_path_and_a_name():
    # An empty path token gives no pair. Kills L1046 `path and name` -> `or`.
    assert build_community_membership({":1-2:function:g": 1}) == {}


def test_community_credit_rejects_mismatched_tag_lists():
    # One tag list per result; a mismatch is a caller bug. Kills L1079 strict=True -> False.
    with pytest.raises(ValueError, match="zip"):
        expand_retrieved_with_community_credit(["a.py:1-2:function:a"], [], [], {})


def test_community_credit_keeps_going_after_a_duplicate():
    # Kills L1082 `continue` -> `break`.
    out = expand_retrieved_with_community_credit(
        ["f.py:1-9:function:f", "f.py:20-30:function:f", "g.py:1-2:function:g"],
        [None, None, None],
        [],
        {},
    )
    assert out == ["f.py:function:f", "g.py:function:g"]


def test_community_credit_keeps_the_chunks_own_id_when_it_is_also_a_gold():
    # Kills L1096 `{normalized} | contained` -> `^`.
    community = {7: frozenset({("f.py", "f"), ("f.py", "g")})}
    golds = ["f.py:function:f", "f.py:function:g"]
    out = expand_retrieved_with_community_credit(
        ["f.py:1-9:function:f"], [["community:7"]], golds, community
    )
    assert out == [{"f.py:function:f", "f.py:function:g"}]
