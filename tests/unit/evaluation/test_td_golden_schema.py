"""Schema guard for the TD network goldens (ADR-0062 Part D2).

`evaluation/td_golden.json` feeds `run_sscg_benchmark.py`; `evaluation/
td_caller_golden.json` feeds `run_caller_recall.py --relationship-types`.
Both encode conventions that fail silently when broken: a bare `D` category
is dropped by the SSCG runner, a bare `F` is routed through find_similar, a
line-ranged id never matches the normalized index, and an `edge_fields` name
that is not a `get_relationship_field_mapping()` field simply yields no
edges. Drift of the ids themselves is covered by test_golden_set_guard.py.
"""

import json
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
EVALUATION_DIR = REPO_ROOT / "evaluation"
TD_GOLDEN = EVALUATION_DIR / "td_golden.json"
TD_CALLER_GOLDEN = EVALUATION_DIR / "td_caller_golden.json"

_LINE_RANGE = re.compile(r":\d+-\d+:")
_TD_KINDS = {"operator", "network", "class"}
_DIRECTED_TD_TYPES = (
    "wires_to",
    "docked_to",
    "contains",
    "references_op",
    "binds_to",
    "exports_to",
    "scripted_by",
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_td_chunk_id(chunk_id: str, where: str) -> None:
    parts = chunk_id.split(":")
    assert len(parts) == 3, f"{where}: {chunk_id!r} is not file:kind:name"
    file_part, kind, name = parts
    assert file_part.endswith(".tdgraph.json"), f"{where}: {chunk_id!r}"
    assert not file_part.startswith(("/", "tests/")), (
        f"{where}: {chunk_id!r} must be relative to _meta.project_path"
    )
    assert kind in _TD_KINDS, f"{where}: kind {kind!r} not in {_TD_KINDS}"
    assert name, f"{where}: empty name in {chunk_id!r}"
    assert not _LINE_RANGE.search(chunk_id), f"{where}: line range in {chunk_id!r}"


@pytest.fixture(scope="module")
def td_golden() -> dict:
    return _load(TD_GOLDEN)


@pytest.fixture(scope="module")
def td_caller_golden() -> dict:
    return _load(TD_CALLER_GOLDEN)


class TestTdGolden:
    def test_meta_and_thresholds(self, td_golden):
        meta = td_golden["_meta"]
        for key in (
            "description",
            "project_path",
            "requires",
            "normalization",
            "total_queries",
            "categories",
            "splits",
        ):
            assert key in meta, key
        assert (REPO_ROOT / meta["project_path"]).is_dir()
        assert meta["total_queries"] == len(td_golden["queries"])
        assert set(td_golden["thresholds"]) >= {"mrr", "recall_at_5", "hit_rate_at_5"}
        assert sum(meta["splits"].values()) == len(td_golden["queries"])

    def test_query_shape(self, td_golden):
        ids = [q["id"] for q in td_golden["queries"]]
        assert len(ids) == len(set(ids)), "duplicate query ids"
        for q in td_golden["queries"]:
            for key in (
                "id",
                "query",
                "category",
                "split",
                "expected",
                "expected_primary",
                "relevance_grades",
            ):
                assert key in q, f"{q.get('id')}: missing {key}"
            assert q["split"] in {"train", "val", "test"}, q["id"]
            assert q["expected"], f"{q['id']}: empty expected"
            assert set(q["expected_primary"]) <= set(q["expected"]), q["id"]
            assert set(q["expected"]) <= set(q["relevance_grades"]), q["id"]
            for cid, grade in q["relevance_grades"].items():
                _assert_td_chunk_id(cid, q["id"])
                assert grade in (0, 1, 2, 3), f"{q['id']}: grade {grade!r}"
                assert (cid in q["expected"]) == (grade >= 2), f"{q['id']}: {cid}"
                assert (cid in q["expected_primary"]) == (grade == 3), (
                    f"{q['id']}: {cid}"
                )

    def test_categories_are_not_bare_letters(self, td_golden):
        """Bare 'D' is dropped and bare 'F' rerouted by run_sscg_benchmark.py."""
        for q in td_golden["queries"]:
            assert re.fullmatch(r"T[A-Z]", q["category"]), (
                f"{q['id']}: {q['category']!r}"
            )
            assert q["category"] in td_golden["_meta"]["categories"], q["id"]


class TestTdCallerGolden:
    def test_meta(self, td_caller_golden):
        meta = td_caller_golden["_meta"]
        assert (REPO_ROOT / meta["project_path"]).is_dir()
        assert "--relationship-types" in meta["usage"]
        assert meta["total_queries"] == len(td_caller_golden["queries"])

    def test_query_shape(self, td_caller_golden):
        from chunking.relationships.relationship_types import (
            get_relationship_field_mapping,
        )

        fields: set[str] = set()
        for fwd, rev in get_relationship_field_mapping().values():
            fields.update((fwd, rev))
        ids = [q["id"] for q in td_caller_golden["queries"]]
        assert len(ids) == len(set(ids)), "duplicate query ids"
        for q in td_caller_golden["queries"]:
            for key in (
                "id",
                "category",
                "description",
                "target_chunk_id",
                "edge_fields",
                "expected_callers",
            ):
                assert key in q, f"{q.get('id')}: missing {key}"
            _assert_td_chunk_id(q["target_chunk_id"], q["id"])
            assert q["edge_fields"], f"{q['id']}: empty edge_fields"
            for field in q["edge_fields"]:
                assert field in fields, f"{q['id']}: unknown edge field {field!r}"
            assert q["expected_callers"], f"{q['id']}: empty expected_callers"
            for cid in q["expected_callers"]:
                _assert_td_chunk_id(cid, q["id"])
                assert cid != q["target_chunk_id"], f"{q['id']}: self-edge"

    def test_every_directed_td_relationship_type_is_exercised(self, td_caller_golden):
        """Each directed TD edge kind appears in at least one query.

        `shares_tag` is symmetric grouping noise and deliberately unbenchmarked.
        """
        from chunking.relationships.relationship_types import (
            get_relationship_field_mapping,
        )

        mapping = get_relationship_field_mapping()
        used = {f for q in td_caller_golden["queries"] for f in q["edge_fields"]}
        for rel in _DIRECTED_TD_TYPES:
            fwd, rev = mapping[rel]
            assert used & {fwd, rev}, f"{rel} not exercised ({fwd}/{rev})"
