"""Tests for search.storage_layout — model-directory naming.

Two tests, answering different questions; do not merge them.

1. Equivalence: pins ``project_id_from_model_dir_name`` to the *old code's*
   semantics (``name.rsplit("_", 1)[0]``) across an adversarial corpus.
2. Anchor: drives the real ``get_project_storage_dir()`` and reconstructs the
   expected ``project_id`` from an oracle independent of the directory name
   (the ``project_info.json`` sidecar).

No round-trip property test — see the plan: it would be vacuous, since the
appended token is always ``f"{dimension}d"`` for an ``int`` dimension, which
can never contain an underscore.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from search.storage_layout import (
    MODEL_DIR_TEMPLATE,
    build_model_dir_name,
    project_id_from_index_dir,
    project_id_from_model_dir_name,
)


# ---------------------------------------------------------------------------
# build_model_dir_name
# ---------------------------------------------------------------------------


class TestBuildModelDirName:
    def test_matches_template(self) -> None:
        name = build_model_dir_name("myproject", "caf2e75a", "qwen3-0.6b", 1024)
        assert name == "myproject_caf2e75a_qwen3-0.6b_1024d"
        assert name == MODEL_DIR_TEMPLATE.format(
            project_name="myproject",
            project_hash="caf2e75a",
            model_slug="qwen3-0.6b",
            dimension=1024,
        )


# ---------------------------------------------------------------------------
# project_id_from_model_dir_name — equivalence test (commit gate)
# ---------------------------------------------------------------------------

ADVERSARIAL_CORPUS = [
    "myproject_caf2e75a_qwen3_0.6b_1024d",  # dots and underscores in the slug
    "myproject_caf2e75a_f2llm-v2-0.6b_1024d",
    "myproject_caf2e75a_qwen3_1024d",  # legacy (no explicit slug segment)
    "myproject_caf2e75a_bge-m3_1024d",
    "no-underscore",  # degenerate: rsplit returns unchanged
    "trailing_underscore_",
    "",  # empty string
]


@pytest.mark.parametrize("name", ADVERSARIAL_CORPUS)
def test_project_id_from_model_dir_name_matches_rsplit(name: str) -> None:
    """Pins the new function to the exact semantics of the six call sites
    it replaces: ``name.rsplit("_", 1)[0]``."""
    assert project_id_from_model_dir_name(name) == name.rsplit("_", 1)[0]


def test_project_id_from_model_dir_name_is_total() -> None:
    """Total function — never raises, including on inputs with no underscore."""
    for name in ("", "no-underscore", "_", "__"):
        project_id_from_model_dir_name(name)  # must not raise


def test_project_id_from_index_dir_uses_parent_name(tmp_path: Path) -> None:
    model_dir = tmp_path / "myproject_caf2e75a_qwen3-0.6b_1024d"
    index_dir = model_dir / "index"
    index_dir.mkdir(parents=True)
    assert project_id_from_index_dir(index_dir) == "myproject_caf2e75a_qwen3-0.6b"


# ---------------------------------------------------------------------------
# Anchor: get_project_storage_dir() end-to-end
# ---------------------------------------------------------------------------


class TestAnchorAgainstRealStorageDir:
    """Drives the real storage-dir creation and checks storage_layout's
    output against the project_info.json sidecar it writes — an oracle
    genuinely independent of the directory name."""

    def test_project_id_matches_project_info_sidecar(self, tmp_path: Path) -> None:
        from mcp_server.storage_manager import get_project_storage_dir

        project_dir = tmp_path / "myproject"
        project_dir.mkdir()
        storage_dir = tmp_path / "storage"
        (storage_dir / "projects").mkdir(parents=True)

        fake_config = MagicMock()
        fake_config.embedding.model_name = "Qwen/Qwen3-Embedding-0.6B"

        with (
            patch(
                "mcp_server.storage_manager.get_storage_dir",
                return_value=storage_dir,
            ),
            patch(
                "mcp_server.storage_manager.get_search_config",
                return_value=fake_config,
            ),
        ):
            model_dir = get_project_storage_dir(str(project_dir))

        info = json.loads((model_dir / "project_info.json").read_text())
        expected_project_id = build_model_dir_name(
            info["project_name"],
            info["project_hash"],
            "qwen3-0.6b",
            info["model_dimension"],
        ).rsplit("_", 1)[0]

        assert project_id_from_model_dir_name(model_dir.name) == expected_project_id
