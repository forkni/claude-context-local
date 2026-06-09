"""Unit tests for CallGraphConfig and ImpactReport callee fields."""

from __future__ import annotations

import pytest


class TestCallGraphConfig:
    def test_default_resolvers(self) -> None:
        from search.config import CallGraphConfig

        cfg = CallGraphConfig()
        assert cfg.resolvers == ["pyan", "libcst"]

    def test_default_lsp_disabled(self) -> None:
        from search.config import CallGraphConfig

        cfg = CallGraphConfig()
        assert cfg.lsp_enabled is False
        assert cfg.lsp_timeout_seconds == 30.0

    def test_custom_resolvers(self) -> None:
        from search.config import CallGraphConfig

        cfg = CallGraphConfig(resolvers=["pyan"])
        assert cfg.resolvers == ["pyan"]

    def test_lsp_enabled(self) -> None:
        from search.config import CallGraphConfig

        cfg = CallGraphConfig(lsp_enabled=True, lsp_timeout_seconds=60.0)
        assert cfg.lsp_enabled is True
        assert cfg.lsp_timeout_seconds == 60.0

    def test_search_config_includes_call_graph(self) -> None:
        from search.config import CallGraphConfig, SearchConfig

        sc = SearchConfig()
        assert hasattr(sc, "call_graph")
        assert isinstance(sc.call_graph, CallGraphConfig)

    def test_search_config_custom_call_graph(self) -> None:
        from search.config import CallGraphConfig, SearchConfig

        cfg = CallGraphConfig(resolvers=["pyan"])
        sc = SearchConfig(call_graph=cfg)
        assert sc.call_graph.resolvers == ["pyan"]

    def test_call_graph_in_subconfig_fields(self) -> None:
        from search.config import SearchConfig

        assert "call_graph" in SearchConfig._SUBCONFIG_FIELDS

    def test_call_graph_in_subconfig_names(self) -> None:
        from search.config import SearchConfig

        assert "call_graph" in SearchConfig._SUBCONFIG_NAMES

    def test_call_graph_in_subconfig_types(self) -> None:
        from search.config import CallGraphConfig, SearchConfig

        assert SearchConfig._SUBCONFIG_TYPES["call_graph"] is CallGraphConfig

    def test_to_dict_roundtrip(self) -> None:
        """SearchConfig to_dict / from_dict must survive a call_graph round-trip."""
        from search.config import CallGraphConfig, SearchConfig

        sc = SearchConfig(call_graph=CallGraphConfig(resolvers=["pyan"]))
        d = sc.to_dict()
        assert "call_graph" in d
        assert d["call_graph"]["resolvers"] == ["pyan"]

        sc2 = SearchConfig.from_dict(d)
        assert sc2.call_graph.resolvers == ["pyan"]

    # -----------------------------------------------------------------
    # New fields: use_pyproject_toml + min_confidence (Task 14)
    # -----------------------------------------------------------------

    def test_use_pyproject_toml_default_false(self) -> None:
        from search.config import CallGraphConfig

        assert CallGraphConfig().use_pyproject_toml is False

    def test_use_pyproject_toml_set_true(self) -> None:
        from search.config import CallGraphConfig

        cfg = CallGraphConfig(use_pyproject_toml=True)
        assert cfg.use_pyproject_toml is True

    def test_min_confidence_default_zero(self) -> None:
        from search.config import CallGraphConfig

        assert CallGraphConfig().min_confidence == 0.0

    def test_min_confidence_custom(self) -> None:
        from search.config import CallGraphConfig

        cfg = CallGraphConfig(min_confidence=0.75)
        assert cfg.min_confidence == pytest.approx(0.75)

    def test_new_fields_survive_to_dict_roundtrip(self) -> None:
        """use_pyproject_toml and min_confidence must survive SearchConfig serialisation."""
        from search.config import CallGraphConfig, SearchConfig

        sc = SearchConfig(
            call_graph=CallGraphConfig(use_pyproject_toml=True, min_confidence=0.75)
        )
        d = sc.to_dict()
        assert d["call_graph"]["use_pyproject_toml"] is True
        assert abs(d["call_graph"]["min_confidence"] - 0.75) < 1e-9

        sc2 = SearchConfig.from_dict(d)
        assert sc2.call_graph.use_pyproject_toml is True
        assert sc2.call_graph.min_confidence == pytest.approx(0.75)


class TestImpactReportCalleeFields:
    def _make_report(self, **kwargs):
        from search.types import ImpactReport

        defaults: dict = {
            "symbol": {},
            "chunk_id": "a.py:1-2:function:f",
            "direct_callers": [],
            "indirect_callers": [],
            "similar_code": [],
            "total_impacted": 0,
            "unique_files": set(),
            "dependency_graph": {},
        }
        defaults.update(kwargs)
        return ImpactReport(**defaults)

    def test_default_callees_empty(self) -> None:
        report = self._make_report()
        assert report.direct_callees == []
        assert report.direct_callees_exact == 0
        assert report.direct_callees_recovered == 0
        assert report.direct_callees_ambiguous == 0

    def test_to_dict_omits_empty_callees(self) -> None:
        report = self._make_report()
        d = report.to_dict()
        assert "direct_callees" not in d
        assert "callee_confidence" not in d

    def test_to_dict_includes_callees_when_set(self) -> None:
        callee = {"chunk_id": "b.py:3-4:function:g", "confidence": "exact"}
        report = self._make_report(
            direct_callees=[callee],
            direct_callees_exact=1,
        )
        d = report.to_dict()
        assert "direct_callees" in d
        assert d["direct_callees"] == [callee]
        assert "callee_confidence" in d
        assert d["callee_confidence"]["exact"] == 1

    def test_to_dict_callee_confidence_breakdown(self) -> None:
        report = self._make_report(
            direct_callees=[{}],
            direct_callees_exact=2,
            direct_callees_recovered=1,
            direct_callees_ambiguous=0,
        )
        d = report.to_dict()
        conf = d["callee_confidence"]
        assert conf["exact"] == 2
        assert conf["recovered"] == 1
        assert conf["ambiguous"] == 0

    def test_callee_confidence_omitted_when_all_zero(self) -> None:
        report = self._make_report(
            direct_callees=[{}],
            direct_callees_exact=0,
            direct_callees_recovered=0,
            direct_callees_ambiguous=0,
        )
        d = report.to_dict()
        assert "callee_confidence" not in d

    def test_caller_confidence_still_present(self) -> None:
        """Adding callee fields must not disturb the existing caller_confidence block."""
        report = self._make_report(
            direct_callers=[{}],
            direct_callers_exact=3,
        )
        d = report.to_dict()
        assert "caller_confidence" in d
        assert d["caller_confidence"]["exact"] == 3
