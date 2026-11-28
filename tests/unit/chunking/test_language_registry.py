"""Unit tests for ADR-0062's extension-key and TD-network-indexing gate helpers
in chunking/language_registry.py, plus the two consumption points that must
honor the gate: MultiLanguageChunker.is_supported() and
TreeSitterChunker.get_supported_extensions()."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestExtensionKey:
    """extension_key() must prefer compound extensions over Path.suffix."""

    def test_compound_extension_recognized(self) -> None:
        from chunking.language_registry import extension_key

        assert extension_key("Graph/Test_network.tdgraph.json") == ".tdgraph.json"

    def test_compound_extension_case_insensitive(self) -> None:
        from chunking.language_registry import extension_key

        assert extension_key("Graph/Test_Network.TDGRAPH.JSON") == ".tdgraph.json"

    def test_plain_json_not_misidentified_as_tdgraph(self) -> None:
        from chunking.language_registry import extension_key

        assert extension_key("package.json") == ".json"

    def test_ordinary_extension_falls_back_to_path_suffix(self) -> None:
        from chunking.language_registry import extension_key

        assert extension_key("chunking/tree_sitter.py") == ".py"

    def test_no_extension_returns_empty_string(self) -> None:
        from chunking.language_registry import extension_key

        assert extension_key("Makefile") == ""


@pytest.mark.parametrize(
    "path",
    [
        "src/lib.rs",
        "SRC/MAIN.PY",
        "dir.with.dots/file",
        ".gitignore",
        "dir/.env.local",
        "name.",
        "dir/name..",
        "archive.tar.gz",
        "Makefile",
        "C:\\proj\\src\\mod.RS",
        "a/b.c/",
    ],
    ids=[
        "plain",
        "upper",
        "dotted-dir",
        "dotfile",
        "dotfile-ext",
        "trailing-dot",
        "two-trailing-dots",
        "double-ext",
        "no-ext",
        "windows-sep",
        "trailing-slash",
    ],
)
def test_extension_key_matches_path_suffix(path: str) -> None:
    """Without a compound match, extension_key gives Path(path).suffix.lower()."""
    from pathlib import Path

    from chunking.language_registry import extension_key

    assert extension_key(path) == Path(path).suffix.lower()


class TestTdPythonMirror:
    """`*__td.txt` TouchDesigner DAT mirrors are indexed as Python, always on
    (not behind the ADR-0062 enable_td_network_indexing gate)."""

    MIRROR = "td/src/hubApi__Text__HubApi__td.txt"

    def test_extension_key_resolves_compound_suffix(self) -> None:
        from chunking.language_registry import extension_key

        assert extension_key(self.MIRROR) == "__td.txt"
        assert extension_key(self.MIRROR.upper()) == "__td.txt"

    def test_plain_txt_stays_unsupported(self) -> None:
        from chunking.language_registry import extension_key
        from chunking.multi_language_chunker import MultiLanguageChunker

        assert extension_key("notes.txt") == ".txt"
        assert MultiLanguageChunker().is_supported("notes.txt") is False

    def test_supported_with_td_gate_off(self) -> None:
        from chunking.multi_language_chunker import MultiLanguageChunker

        with patch("search.config.get_chunking_config", return_value=None):
            assert MultiLanguageChunker().is_supported(self.MIRROR) is True

    def test_in_supported_extensions_regardless_of_gate(self) -> None:
        from chunking.tree_sitter import TreeSitterChunker

        for gate in (False, True):
            with patch(
                "chunking.tree_sitter.td_network_indexing_enabled", return_value=gate
            ):
                assert "__td.txt" in TreeSitterChunker.get_supported_extensions()

    def test_routes_to_python_chunker(self) -> None:
        from chunking.languages.python import PythonChunker
        from chunking.tree_sitter import TreeSitterChunker

        chunker = TreeSitterChunker().get_chunker(self.MIRROR)
        assert isinstance(chunker, PythonChunker)

    def test_chunks_file_as_python(self, tmp_path) -> None:
        from chunking.multi_language_chunker import MultiLanguageChunker

        mirror = tmp_path / "foo__Text__Foo__td.txt"
        mirror.write_text("def f():\n    return 1\n", encoding="utf-8")
        chunks = MultiLanguageChunker(str(tmp_path)).chunk_file(str(mirror))
        functions = [c for c in chunks if c.chunk_type == "function"]
        assert len(functions) == 1
        assert functions[0].language == "python"


class TestIsTdNetworkFile:
    def test_matches_compound_extension(self) -> None:
        from chunking.language_registry import is_td_network_file

        assert is_td_network_file("Graph/Test_network.tdgraph.json") is True

    def test_rejects_plain_json(self) -> None:
        from chunking.language_registry import is_td_network_file

        assert is_td_network_file("package.json") is False

    def test_rejects_python_file(self) -> None:
        from chunking.language_registry import is_td_network_file

        assert is_td_network_file("chunking/tree_sitter.py") is False


class TestTdNetworkIndexingEnabled:
    """The master gate (ADR-0062): default-safe False, opt-in True."""

    def test_false_when_config_unavailable(self) -> None:
        from chunking.language_registry import td_network_indexing_enabled

        with patch("search.config.get_chunking_config", return_value=None):
            assert td_network_indexing_enabled() is False

    def test_false_when_flag_off(self) -> None:
        from chunking.language_registry import td_network_indexing_enabled

        mock_config = MagicMock()
        mock_config.enable_td_network_indexing = False
        with patch("search.config.get_chunking_config", return_value=mock_config):
            assert td_network_indexing_enabled() is False

    def test_true_when_flag_on(self) -> None:
        from chunking.language_registry import td_network_indexing_enabled

        mock_config = MagicMock()
        mock_config.enable_td_network_indexing = True
        with patch("search.config.get_chunking_config", return_value=mock_config):
            assert td_network_indexing_enabled() is True


class TestMultiLanguageChunkerGate:
    """MultiLanguageChunker.is_supported() must honor the gate for .tdgraph.json
    while staying byte-identical for every other extension regardless of it."""

    def test_tdgraph_unsupported_when_gate_off(self) -> None:
        from chunking.multi_language_chunker import MultiLanguageChunker

        chunker = MultiLanguageChunker()
        with patch("search.config.get_chunking_config", return_value=None):
            assert chunker.is_supported("Graph/Test_network.tdgraph.json") is False

    def test_tdgraph_supported_when_gate_on(self) -> None:
        from chunking.multi_language_chunker import MultiLanguageChunker

        chunker = MultiLanguageChunker()
        mock_config = MagicMock()
        mock_config.enable_td_network_indexing = True
        with patch("search.config.get_chunking_config", return_value=mock_config):
            assert chunker.is_supported("Graph/Test_network.tdgraph.json") is True

    def test_python_file_unaffected_by_gate_state(self) -> None:
        from chunking.multi_language_chunker import MultiLanguageChunker

        chunker = MultiLanguageChunker()
        with patch("search.config.get_chunking_config", return_value=None):
            assert chunker.is_supported("chunking/tree_sitter.py") is True

    def test_plain_json_stays_unsupported(self) -> None:
        """Registering .tdgraph.json must not widen plain .json support."""
        from chunking.multi_language_chunker import MultiLanguageChunker

        chunker = MultiLanguageChunker()
        mock_config = MagicMock()
        mock_config.enable_td_network_indexing = True
        with patch("search.config.get_chunking_config", return_value=mock_config):
            assert chunker.is_supported("package.json") is False


class TestTreeSitterGetSupportedExtensionsGate:
    """get_supported_extensions() feeds the file walker / Merkle-hash extension
    set (incremental_indexer.py, index_freshness.py, index_handlers.py) -- it
    must only include .tdgraph.json when the feature is enabled."""

    def test_tdgraph_absent_when_gate_off(self) -> None:
        from chunking.tree_sitter import TreeSitterChunker

        with patch(
            "chunking.tree_sitter.td_network_indexing_enabled", return_value=False
        ):
            assert ".tdgraph.json" not in TreeSitterChunker.get_supported_extensions()

    def test_tdgraph_present_when_gate_on(self) -> None:
        from chunking.tree_sitter import TreeSitterChunker

        with patch(
            "chunking.tree_sitter.td_network_indexing_enabled", return_value=True
        ):
            assert ".tdgraph.json" in TreeSitterChunker.get_supported_extensions()

    def test_python_extension_unaffected_by_gate_state(self) -> None:
        from chunking.tree_sitter import TreeSitterChunker

        with patch(
            "chunking.tree_sitter.td_network_indexing_enabled", return_value=False
        ):
            extensions_off = set(TreeSitterChunker.get_supported_extensions())
        with patch(
            "chunking.tree_sitter.td_network_indexing_enabled", return_value=True
        ):
            extensions_on = set(TreeSitterChunker.get_supported_extensions())

        assert extensions_on - extensions_off == {".tdgraph.json"}
        assert ".py" in extensions_off


class TestWgslWholeFileGate:
    """`.wgsl` files are indexed as whole-file chunks unless
    `ChunkingConfig.enable_wgsl_whole_file` is off (ADR-0093)."""

    def _config(self, enabled: bool) -> MagicMock:
        config = MagicMock()
        config.enable_wgsl_whole_file = enabled
        config.enable_td_network_indexing = False
        config.max_file_size_bytes = None
        return config

    def test_gate_follows_the_setting(self) -> None:
        from chunking.language_registry import wgsl_whole_file_enabled

        for enabled in (True, False):
            with patch(
                "search.config.get_chunking_config", return_value=self._config(enabled)
            ):
                assert wgsl_whole_file_enabled() is enabled

    def test_gate_is_on_without_a_config(self) -> None:
        from chunking.language_registry import wgsl_whole_file_enabled

        with patch("search.config.get_chunking_config", return_value=None):
            assert wgsl_whole_file_enabled() is True

    def test_is_supported_follows_the_gate(self) -> None:
        from chunking.multi_language_chunker import MultiLanguageChunker

        chunker = MultiLanguageChunker()
        for enabled in (True, False):
            with patch(
                "search.config.get_chunking_config", return_value=self._config(enabled)
            ):
                assert chunker.is_supported("crates/gpu/decode.wgsl") is enabled

    def test_supported_extensions_follow_the_gate(self) -> None:
        from chunking.tree_sitter import TreeSitterChunker

        with patch("chunking.tree_sitter.wgsl_whole_file_enabled", return_value=False):
            extensions_off = set(TreeSitterChunker.get_supported_extensions())
        with patch("chunking.tree_sitter.wgsl_whole_file_enabled", return_value=True):
            extensions_on = set(TreeSitterChunker.get_supported_extensions())
        assert extensions_on - extensions_off == {".wgsl"}

    def test_wgsl_is_a_pseudo_language(self) -> None:
        """Pseudo-language chunks are never call targets, so a Rust call
        `reduce()` cannot link to `reduce.wgsl` by name."""
        from chunking.language_registry import PSEUDO_LANGUAGES

        assert "wgsl" in PSEUDO_LANGUAGES
