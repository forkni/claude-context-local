"""Drift detection for the ``.tdgraph.json`` whole-document byte budget
(TD_Glossary_tox ADR 0014).

TD_Glossary_tox's ``Extensions/OperatorGlossary/tdgraph_contract.py`` declares
``CHUNKER_MAX_DOC_BYTES`` -- the whole-artifact admission gate a producer export must
fit under, sized from measured per-node/per-edge cost on a full-fidelity POPX-scale
export (18,491,105 B lossless against the old 16 MiB budget, 10.2% over; see
``TD_Glossary_tox/docs/adr/0014-graph-budget-is-24mib-lossless-first-with-measured-size.md``).
That module's docstring states this repo is expected to keep a matching copy of the
number and drift-test it here -- modelled on ``test_td_network_edge_vocabulary.py``'s
two-sided contract for the edge-type vocabulary.

Neither repo imports the other (they are separate git repositories with no packaging
relationship), so this is a literal-vs-literal pin, not an import-based assertion: if
either side's number changes without the other, this test is the only thing that
notices. Update ``_TD_GLOSSARY_TOX_CHUNKER_MAX_DOC_BYTES`` below whenever
``tdgraph_contract.CHUNKER_MAX_DOC_BYTES`` changes.

Background (2026-09-19): the two sides drifted silently before this test existed --
``chunking/multi_language_chunker.py``'s size gate (``:342``) fires *before* the
TD-network dispatch (``:349``), so a producer export over this repo's stale 5 MB cap
was dropped with only an invisible-by-default ``logger.info``, never reaching the
chunker. ``search/config.py``'s ``ChunkingConfig.max_file_size_bytes`` default and the
live, machine-local ``search_config.json`` (the file ``get_chunking_config()`` actually
serves at runtime, not just the ``.example`` template) must both track this number.
"""

import json
import os
from pathlib import Path

import pytest

from chunking.multi_language_chunker import MultiLanguageChunker
from search.config import ChunkingConfig


# Mirrors tdgraph_contract.CHUNKER_MAX_DOC_BYTES in TD_Glossary_tox
# (Extensions/OperatorGlossary/tdgraph_contract.py) -- 24 MiB, TD_Glossary_tox
# ADR 0014 (2026-09-19).
_TD_GLOSSARY_TOX_CHUNKER_MAX_DOC_BYTES = 25_165_824

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FIXTURE_DIR = _REPO_ROOT / "tests" / "fixtures" / "td_network"
_FIXTURE_PATH = _FIXTURE_DIR / "Test_network.tdgraph.json"

# The live POPX export that silently dropped out under the old 5 MB cap
# (F:/STUDIO_ELSEWHERE/Graph/POPX_1_4_0.tdgraph.json, 2026-09-19 incident).
_POPX_SIZED_BYTES = 16_649_428


def test_max_file_size_bytes_matches_td_glossary_tox_contract():
    """The dataclass default must equal the producer's admission gate.

    If a producer-side budget change (TD_Glossary_tox ADR 0014 or its successor)
    lands without a matching change here, TD-network exports silently start
    getting dropped again at ``multi_language_chunker.py``'s size gate -- exactly
    the 2026-09-19 incident this test exists to prevent a repeat of.
    """
    assert (
        ChunkingConfig().max_file_size_bytes == _TD_GLOSSARY_TOX_CHUNKER_MAX_DOC_BYTES
    )


def test_live_search_config_json_is_not_stale():
    """The machine-local ``search_config.json`` -- the file
    ``get_chunking_config()`` actually serves at runtime when present -- must
    carry the same number as the dataclass default, not just
    ``search_config.json.example``. Editing only the example and leaving the
    live file behind was exactly how the 2026-09-19 drift shipped.

    ``search_config.json`` is gitignored (``.gitignore``), so it does not exist
    on a fresh checkout -- skip rather than fail in that case.
    """
    path = _REPO_ROOT / "search_config.json"
    if not path.exists():
        pytest.skip(
            "search_config.json is machine-local (gitignored); nothing to "
            "check on a fresh checkout"
        )
    live_config = json.loads(path.read_text(encoding="utf-8"))
    assert (
        live_config["chunking"]["max_file_size_bytes"]
        == _TD_GLOSSARY_TOX_CHUNKER_MAX_DOC_BYTES
    )


def test_example_search_config_json_is_not_stale():
    """Same check against ``search_config.json.example``, the template new
    installs copy from -- both files must track the dataclass default together."""
    example_config = json.loads(
        (_REPO_ROOT / "search_config.json.example").read_text(encoding="utf-8")
    )
    assert (
        example_config["chunking"]["max_file_size_bytes"]
        == _TD_GLOSSARY_TOX_CHUNKER_MAX_DOC_BYTES
    )


def test_declared_range_still_covers_the_budget():
    """The validation range (1024-100 MiB) is the actual hard ceiling on this
    field. Neither it nor the listwise reranker's VRAM profile (bounded by
    ``top_k_candidates`` x ``listwise_doc_max_chars``, independent of index
    size) scale with graph size. This just confirms a future budget raise has
    not silently exceeded the declared range without anyone widening it on
    purpose.
    """
    field_info = next(
        f
        for f in ChunkingConfig.__dataclass_fields__.values()
        if f.name == "max_file_size_bytes"
    )
    low, high = field_info.metadata["range"]
    assert low <= _TD_GLOSSARY_TOX_CHUNKER_MAX_DOC_BYTES <= high


def test_popx_sized_tdgraph_passes_the_size_gate(monkeypatch):
    """A POPX-scale export must actually reach ``TDNetworkChunker`` under the
    default (24 MiB) cap -- the four tests above only pin numbers, they never
    prove a real oversized-under-the-old-cap file clears the gate.

    ``os.path.getsize`` is monkeypatched to the live POPX file's real size
    (16,649,428 B) rather than growing the checked-in fixture -- the fixture
    stays small and fast; only the size *check* needs to see a big number. The
    fixture itself is well-formed TD network JSON, so once the size gate lets
    it through, the ordinary dispatch path in
    ``test_td_network_chunker.py::test_enabled_dispatches_to_td_network_chunker``
    (22 chunks, all ``td_network``) is exactly what should happen here too.
    """
    import search.config as sc

    cfg = sc.ChunkingConfig(enable_td_network_indexing=True)
    assert cfg.max_file_size_bytes == _TD_GLOSSARY_TOX_CHUNKER_MAX_DOC_BYTES
    monkeypatch.setattr(sc, "get_chunking_config", lambda: cfg)

    real_getsize = os.path.getsize

    def _fake_getsize(path):
        if str(path) == str(_FIXTURE_PATH):
            return _POPX_SIZED_BYTES
        return real_getsize(path)

    monkeypatch.setattr(
        "chunking.multi_language_chunker.os.path.getsize", _fake_getsize
    )

    mc = MultiLanguageChunker(root_path=str(_FIXTURE_DIR))
    assert mc.is_supported(str(_FIXTURE_PATH)) is True
    chunks = mc.chunk_file(str(_FIXTURE_PATH))
    assert len(chunks) == 22
    assert {c.language for c in chunks} == {"td_network"}


def test_old_5mb_cap_would_have_dropped_it(monkeypatch, caplog):
    """Documents the incident, not just the fix: under the stale 5 MB default
    that shipped before this workstream, the same POPX-sized export is
    silently dropped at the size gate with only an INFO-level log line --
    exactly what happened in production on 2026-09-19.
    """
    import search.config as sc

    cfg = sc.ChunkingConfig(
        enable_td_network_indexing=True, max_file_size_bytes=5 * 1024 * 1024
    )
    monkeypatch.setattr(sc, "get_chunking_config", lambda: cfg)

    real_getsize = os.path.getsize

    def _fake_getsize(path):
        if str(path) == str(_FIXTURE_PATH):
            return _POPX_SIZED_BYTES
        return real_getsize(path)

    monkeypatch.setattr(
        "chunking.multi_language_chunker.os.path.getsize", _fake_getsize
    )

    mc = MultiLanguageChunker(root_path=str(_FIXTURE_DIR))
    with caplog.at_level("INFO", logger="chunking.multi_language_chunker"):
        chunks = mc.chunk_file(str(_FIXTURE_PATH))

    assert chunks == []
    assert any(
        "exceeds" in r.message and "max_file_size_bytes" in r.message
        for r in caplog.records
    )
