"""Tests for evaluation.index_locator against a fake storage tree."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.index_locator import (
    AmbiguousIndexError,
    IndexNotFoundError,
    IndexPaths,
    find_index,
    paths_for,
    storage_root,
)


def make_project(
    root: Path,
    name: str,
    *,
    with_db: bool = True,
    graph_names: tuple[str, ...] = ("{id}_call_graph.json",),
) -> Path:
    project_dir = root / "projects" / name
    (project_dir / "index").mkdir(parents=True)
    if with_db:
        (project_dir / "index" / "metadata.db").write_bytes(b"")
    project_id = name.rsplit("_", 1)[0]  # strip the "_1024d" dimension suffix
    for pattern in graph_names:
        (project_dir / pattern.format(id=project_id)).write_text("{}", encoding="utf-8")
    (project_dir / "project_info.json").write_text(
        json.dumps({"project_name": name.split("_")[0], "embedding_model": "x/y"}),
        encoding="utf-8",
    )
    return project_dir


def test_happy_path(tmp_path: Path) -> None:
    project_dir = make_project(tmp_path, "myproj_9e7f0a98_f2llm-v2-0.6b_1024d")
    paths = find_index("myproj", storage=tmp_path)
    assert paths == IndexPaths(
        project_dir=project_dir,
        project_id="myproj_9e7f0a98_f2llm-v2-0.6b",
        metadata_db=project_dir / "index" / "metadata.db",
        call_graph=project_dir / "myproj_9e7f0a98_f2llm-v2-0.6b_call_graph.json",
    )
    assert paths.read_project_info()["embedding_model"] == "x/y"


def test_ambiguous_match_and_model_slug_disambiguation(tmp_path: Path) -> None:
    make_project(tmp_path, "myproj_9e7f0a98_f2llm-v2-0.6b_1024d")
    make_project(tmp_path, "myproj_9e7f0a98_bge-m3_1024d")
    with pytest.raises(AmbiguousIndexError, match="bge-m3"):
        find_index("myproj", storage=tmp_path)
    paths = find_index("myproj", storage=tmp_path, model_slug="BAAI/BGE-M3")
    assert paths.project_dir.name == "myproj_9e7f0a98_bge-m3_1024d"


def test_missing_projects_dir_and_no_match(tmp_path: Path) -> None:
    with pytest.raises(IndexNotFoundError, match="No projects directory"):
        find_index("myproj", storage=tmp_path)
    make_project(tmp_path, "other_1_m_1024d")
    with pytest.raises(IndexNotFoundError, match="No project directory"):
        find_index("myproj", storage=tmp_path)


def test_missing_graph_or_db(tmp_path: Path) -> None:
    no_graph = make_project(tmp_path, "a_1_m_1024d", graph_names=())
    with pytest.raises(IndexNotFoundError, match="found: none"):
        paths_for(no_graph)
    two_graphs = make_project(
        tmp_path,
        "b_1_m_1024d",
        graph_names=("{id}_call_graph.json", "stale_call_graph.json"),
    )
    with pytest.raises(IndexNotFoundError, match="stale_call_graph.json"):
        paths_for(two_graphs)
    no_db = make_project(tmp_path, "c_1_m_1024d", with_db=False)
    with pytest.raises(IndexNotFoundError, match="metadata.db"):
        paths_for(no_db)


def test_storage_root_env_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CODE_SEARCH_STORAGE", str(tmp_path))
    assert storage_root() == tmp_path
    assert storage_root(tmp_path / "x") == tmp_path / "x"
    monkeypatch.delenv("CODE_SEARCH_STORAGE")
    assert storage_root() == Path.home() / ".claude_code_search"
