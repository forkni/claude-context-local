"""Property tests for RRFReranker.rerank (search/reranker.py), Phase 4.1.

Reciprocal Rank Fusion gives each document ``sum_i w_i / (k + rank_i)`` over the lists it
appears in, with the weights normalised to sum to 1. The properties below hold for any input
lists; none of them recomputes a score with the reranker's own formula. They check the
consequences instead: one entry per document, the right length, order by score, agreement
when the input lists are reordered, a prefix relation between short and long cuts, and
dominance (a document ranked better everywhere scores higher).

Break-and-revert evidence (2026-11-18): dropping the cap in _select_with_reserve,
`reserve = min(reserved_slots, max_results)` -> `reserve = reserved_slots`, passes all 40
example tests in test_reranker.py and fails test_reserved_slots_keep_length_and_uniqueness.
Sorting ascending, overwriting instead of summing a document's contributions, and the two
reserve-fill off-by-ones also fail here (the example tests catch those too).
"""

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from search.reranker import RRFReranker, SearchResult


DOC_IDS = [f"m.py:{i}-{i + 1}:function:f{i}" for i in range(12)]


@st.composite
def result_lists(draw: st.DrawFn, min_lists: int = 1) -> list[list[str]]:
    """1-3 ranked lists of distinct doc ids (an id appears at most once per list)."""
    n = draw(st.integers(min_value=min_lists, max_value=3))
    return [
        draw(st.lists(st.sampled_from(DOC_IDS), max_size=8, unique=True))
        for _ in range(n)
    ]


def build(lists: list[list[str]]) -> list[list[SearchResult]]:
    """Fresh SearchResult objects each call: rerank writes into result.metadata."""
    return [
        [
            SearchResult(chunk_id=cid, score=1.0 - rank / 100, metadata={})
            for rank, cid in enumerate(lst)
        ]
        for lst in lists
    ]


def ids_of(results: list[SearchResult]) -> list[str]:
    return [r.chunk_id for r in results]


k_values = st.integers(min_value=1, max_value=200)
cuts = st.integers(min_value=1, max_value=15)


@given(result_lists(), k_values, cuts)
def test_rerank_returns_each_document_once_up_to_max_results(lists, k, max_results):
    out = RRFReranker(k=k).rerank(build(lists), max_results=max_results)
    distinct = {cid for lst in lists for cid in lst}
    assert len(ids_of(out)) == len(set(ids_of(out)))
    assert set(ids_of(out)) <= distinct
    assert len(out) == min(max_results, len(distinct))


@given(result_lists(), k_values, cuts)
def test_rerank_orders_by_non_increasing_rrf_score(lists, k, max_results):
    out = RRFReranker(k=k).rerank(build(lists), max_results=max_results)
    scores = [r.metadata["rrf_score"] for r in out]
    assert scores == sorted(scores, reverse=True)
    assert [r.metadata["final_rank"] for r in out] == list(range(1, len(out) + 1))


@given(result_lists(), k_values, cuts)
def test_appears_in_lists_counts_the_input_lists_holding_the_document(
    lists, k, max_results
):
    out = RRFReranker(k=k).rerank(build(lists), max_results=max_results)
    for r in out:
        assert r.metadata["appears_in_lists"] == sum(r.chunk_id in lst for lst in lists)


@given(result_lists(), k_values, cuts, st.data())
def test_short_cut_is_a_prefix_of_a_long_cut(lists, k, max_results, data):
    longer = data.draw(st.integers(min_value=max_results, max_value=30))
    short = RRFReranker(k=k).rerank(build(lists), max_results=max_results)
    long_ = RRFReranker(k=k).rerank(build(lists), max_results=longer)
    assert ids_of(short) == ids_of(long_)[: len(short)]


@given(result_lists(min_lists=2), k_values, st.permutations(range(3)))
def test_scores_do_not_depend_on_the_order_of_the_input_lists(lists, k, perm):
    order = [i for i in perm if i < len(lists)]
    out = RRFReranker(k=k).rerank(build(lists), max_results=50)
    shuffled = RRFReranker(k=k).rerank(build([lists[i] for i in order]), max_results=50)
    by_id = {r.chunk_id: r.metadata["rrf_score"] for r in out}
    by_id_shuffled = {r.chunk_id: r.metadata["rrf_score"] for r in shuffled}
    assert by_id.keys() == by_id_shuffled.keys()
    for cid, score in by_id.items():
        assert by_id_shuffled[cid] == pytest.approx(score)


@given(
    st.lists(st.sampled_from(DOC_IDS), min_size=1, max_size=10, unique=True), k_values
)
def test_one_list_keeps_its_order(lst, k):
    out = RRFReranker(k=k).rerank(build([lst]), max_results=len(lst))
    assert ids_of(out) == lst


@given(result_lists(min_lists=2), k_values)
def test_a_document_better_ranked_in_every_list_scores_higher(lists, k):
    """Dominance: if a is in every list b is in, and ranked strictly above b in each, and
    also appears in at least one list b is absent from, then a scores higher than b."""
    out = RRFReranker(k=k).rerank(build(lists), max_results=50)
    score = {r.chunk_id: r.metadata["rrf_score"] for r in out}
    rank = [{cid: i for i, cid in enumerate(lst)} for lst in lists]
    pairs = 0
    for a in score:
        for b in score:
            if a == b:
                continue
            dominates = all(
                a in rk and (b not in rk or rk[a] < rk[b])
                for rk in rank
                if a in rk or b in rk
            )
            if dominates:
                pairs += 1
                assert score[a] > score[b]
    assume(pairs > 0)


@given(result_lists(min_lists=2), k_values, cuts, st.integers(min_value=0, max_value=5))
def test_reserved_slots_keep_length_and_uniqueness(lists, k, max_results, reserved):
    out = RRFReranker(k=k).rerank(
        build(lists), max_results=max_results, reserved_slots=reserved
    )
    distinct = {cid for lst in lists for cid in lst}
    assert len(out) == min(max_results, len(distinct))
    assert len(set(ids_of(out))) == len(out)
    # The head (slots not reserved) is plain RRF order, so it is a prefix of the unreserved cut.
    head = max_results - min(reserved, max_results)
    plain = RRFReranker(k=k).rerank(build(lists), max_results=max_results)
    assert ids_of(out)[:head] == ids_of(plain)[:head]
