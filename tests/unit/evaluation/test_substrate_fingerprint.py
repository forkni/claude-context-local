"""Regression tests for the benchmark harness's substrate fingerprint.

Genesis: a 2026-09-14 LSP-tier retrieval gate compared two result files that
silently differed in corpus size (2991 vs 2992 chunks, captured 5 hours
apart, one commit landing in between). The old ``config_metadata`` block
(``project_path``/``k``/``category_filter``/``split_filter`` only) had no way
to catch this, and a false "retrieval-neutral" verdict nearly got pinned as
canon before the drift was found by hand.

``_build_substrate_fingerprint`` (``scripts/benchmark/run_sscg_benchmark.py``)
closes that gap by recording corpus size, embedding model, resolver-edge
mix, and git SHA into every run's ``config_metadata["substrate"]``.
``_check_substrate_confound`` is the ``--compare``-time guard that reads it
back and prints a loud ``[CONFOUND]`` warning instead of silently comparing
two different substrates.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from scripts.benchmark.run_sscg_benchmark import (
    _build_substrate_fingerprint,
    _check_substrate_confound,
)


def _make_searcher(
    *,
    total_chunks: int = 2992,
    files_indexed: int = 238,
    resolver_edges: dict[str, int] | None = None,
) -> MagicMock:
    resolver_edges = resolver_edges if resolver_edges is not None else {}
    searcher = MagicMock()
    searcher.dense_index.get_stats.return_value = {
        "total_chunks": total_chunks,
        "files_indexed": files_indexed,
    }
    edges = []
    for source, count in resolver_edges.items():
        edges.extend([("a", "b", {"resolver_source": source})] * count)
    searcher.dense_index.graph_integration.storage.graph.edges.return_value = edges
    return searcher


def _make_cfg(
    *, model_name: str = "BAAI/bge-m3", dimension: int = 1024, lsp_enabled: bool = True
) -> MagicMock:
    cfg = MagicMock()
    cfg.embedding.model_name = model_name
    cfg.embedding.dimension = dimension
    cfg.call_graph.lsp_enabled = lsp_enabled
    cfg.call_graph.resolvers = ["pyan", "libcst"]
    return cfg


def test_fingerprint_captures_corpus_size():
    """total_chunks/files_indexed come from CodeIndexManager.get_stats(), not
    a timestamp -- the direct fix for the 2991-vs-2992 confound."""
    searcher = _make_searcher(total_chunks=2992, files_indexed=238)
    cfg = _make_cfg()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        fingerprint = _build_substrate_fingerprint(searcher, cfg)

    assert fingerprint["total_chunks"] == 2992
    assert fingerprint["files_indexed"] == 238


def test_fingerprint_captures_embedding_model_and_lsp_flag():
    searcher = _make_searcher()
    cfg = _make_cfg(model_name="BAAI/bge-m3", dimension=1024, lsp_enabled=True)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        fingerprint = _build_substrate_fingerprint(searcher, cfg)

    assert fingerprint["embedding_model"] == "BAAI/bge-m3"
    assert fingerprint["embedding_dimension"] == 1024
    assert fingerprint["lsp_enabled"] is True
    assert fingerprint["resolvers"] == ["pyan", "libcst"]


def test_fingerprint_counts_edges_by_resolver_source():
    """The three-tier oracle from commit 2779916a: lsp 1960 / libcst 759 /
    pyan 556 -- confirms the counter groups by resolver_source correctly."""
    searcher = _make_searcher(resolver_edges={"lsp": 1960, "libcst": 759, "pyan": 556})
    cfg = _make_cfg()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        fingerprint = _build_substrate_fingerprint(searcher, cfg)

    assert fingerprint["resolver_edge_counts"] == {
        "lsp": 1960,
        "libcst": 759,
        "pyan": 556,
    }


def test_fingerprint_captures_git_sha_and_dirty_flag():
    searcher = _make_searcher()
    cfg = _make_cfg()

    def fake_run(cmd, **kwargs):
        if cmd[:2] == ["git", "rev-parse"]:
            return MagicMock(returncode=0, stdout="2779916a1234\n")
        if cmd[:2] == ["git", "status"]:
            return MagicMock(returncode=0, stdout=" M docs/BENCHMARKS.md\n")
        raise AssertionError(f"unexpected subprocess call: {cmd}")

    with patch("subprocess.run", side_effect=fake_run):
        fingerprint = _build_substrate_fingerprint(searcher, cfg)

    assert fingerprint["git_sha"] == "2779916a1234"
    assert fingerprint["git_dirty"] is True


def test_fingerprint_is_best_effort_on_missing_attributes():
    """A searcher missing dense_index (e.g. a bare test double) must not
    crash fingerprint capture -- each field degrades independently."""
    searcher = MagicMock(spec=[])  # no attributes at all
    cfg = _make_cfg()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        fingerprint = _build_substrate_fingerprint(searcher, cfg)

    assert "total_chunks" not in fingerprint
    # embedding/lsp fields come from cfg, which is still a valid mock
    assert fingerprint["embedding_model"] == "BAAI/bge-m3"


def _run(config_name: str, **substrate_overrides) -> dict:
    substrate = {
        "total_chunks": 2992,
        "files_indexed": 238,
        "embedding_model": "BAAI/bge-m3",
        "git_sha": "2779916a",
    }
    substrate.update(substrate_overrides)
    return {
        "config_name": config_name,
        "config_metadata": {"substrate": substrate},
        "per_query": [],
    }


def test_confound_guard_silent_when_substrates_match(capsys):
    r1 = _run("control")
    r2 = _run("treatment")

    _check_substrate_confound(r1, r2)

    assert "[CONFOUND]" not in capsys.readouterr().out


def test_confound_guard_fires_on_chunk_count_mismatch(capsys):
    """The exact 2026-09-14 scenario: 2991 vs 2992 total_chunks."""
    r1 = _run("control", total_chunks=2991)
    r2 = _run("treatment", total_chunks=2992)

    _check_substrate_confound(r1, r2)

    out = capsys.readouterr().out
    assert "[CONFOUND]" in out
    assert "total_chunks" in out
    assert "2991" in out and "2992" in out


def test_confound_guard_fires_on_git_sha_mismatch(capsys):
    r1 = _run("control", git_sha="aaaa111")
    r2 = _run("treatment", git_sha="bbbb222")

    _check_substrate_confound(r1, r2)

    assert "[CONFOUND]" in capsys.readouterr().out


def test_confound_guard_skips_result_files_predating_fingerprint(capsys):
    """Older result JSONs have no ``substrate`` key at all -- nothing to
    compare against, so this must not be misread as a confound."""
    r1 = {"config_name": "old_run", "config_metadata": {}, "per_query": []}
    r2 = _run("new_run")

    _check_substrate_confound(r1, r2)

    assert "[CONFOUND]" not in capsys.readouterr().out
