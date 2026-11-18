"""Property tests for the chunk_id wire format owner (search/chunk_id.py), Phase 4.1.

``file:start-end:kind:name`` is parsed on every search and evaluation path, so a parser bug
there changes what counts as "the same hit". Properties:

- round trip: ``ChunkId.parse(str(c)) == c`` for any well-formed ChunkId;
- idempotency: ``normalize`` and ``dedup_key`` are no-ops on their own output (both
  docstrings promise this);
- line-range invariance: two ids that differ only in their line range share a dedup key,
  and ``split_block`` shares one with ``method`` (the documented collapse);
- separator invariance: a Windows-style path gives the same key as the forward-slash path.

Break-and-revert evidence (2026-11-18, hand mutants in search/chunk_id.py, each fails a
property here): no split_block collapse; `while "//"` -> `while "///"`; line count without
the `+ 1`; `line_end=start` in parse. test_chunk_id.py also catches all four, so these
properties widen the inputs (generated paths, names, separators) rather than add a kill.
"""

from hypothesis import given
from hypothesis import strategies as st

from search.chunk_id import ChunkId, dedup_key, extract_line_count, normalize


# Path segments, kinds and names never contain ':' (the field separator) or '\' / '/'
# (path separators, generated separately), matching what the chunkers emit.
segment = st.text(
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_.-"
    ),
    min_size=1,
    max_size=12,
)
rel_paths = st.lists(segment, min_size=1, max_size=4).map("/".join)
kinds = st.sampled_from(
    ["function", "class", "method", "module", "decorated_definition"]
)
names = st.lists(segment, min_size=1, max_size=3).map(".".join)


@st.composite
def chunk_ids(draw: st.DrawFn) -> ChunkId:
    start = draw(st.integers(min_value=1, max_value=5000))
    end = draw(st.integers(min_value=start, max_value=start + 500))
    return ChunkId(
        file_path=draw(rel_paths),
        line_start=start,
        line_end=end,
        kind=draw(kinds),
        name=draw(names),
    )


@given(chunk_ids())
def test_parse_round_trips_the_wire_format(cid):
    assert ChunkId.parse(str(cid)) == cid


@given(chunk_ids())
def test_extract_line_count_agrees_with_the_parsed_range(cid):
    assert extract_line_count(str(cid)) == cid.line_end - cid.line_start + 1


@given(chunk_ids(), st.sampled_from(["\\", "\\\\", "//", "/"]))
def test_normalize_is_idempotent_and_canonicalises_separators(cid, sep):
    raw = str(cid).replace("/", sep)
    once = normalize(raw)
    assert normalize(once) == once
    assert once == str(cid)


@given(chunk_ids())
def test_dedup_key_is_idempotent(cid):
    key = dedup_key(str(cid))
    assert dedup_key(key) == key


@given(chunk_ids(), st.integers(min_value=1, max_value=900), st.integers(0, 900))
def test_dedup_key_ignores_the_line_range(cid, start, length):
    moved = ChunkId(cid.file_path, start, start + length, cid.kind, cid.name)
    assert dedup_key(str(moved)) == dedup_key(str(cid))
    assert dedup_key(str(cid)) == f"{cid.file_path}:{cid.kind}:{cid.name}"


@given(chunk_ids())
def test_split_block_fragments_share_the_method_key(cid):
    fragment = ChunkId(
        cid.file_path, cid.line_start, cid.line_end, "split_block", cid.name
    )
    method = ChunkId(cid.file_path, cid.line_start, cid.line_end, "method", cid.name)
    assert dedup_key(str(fragment)) == dedup_key(str(method))


@given(chunk_ids(), st.sampled_from(["\\", "\\\\"]))
def test_dedup_key_ignores_windows_separators(cid, sep):
    windows = str(cid).replace("/", sep)
    assert dedup_key(windows) == dedup_key(str(cid))
