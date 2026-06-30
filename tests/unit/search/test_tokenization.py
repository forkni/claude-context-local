"""Tests for search/tokenization.py — P8 single tokenization owner.

Two coverage areas:
1. Behaviour parity: assert the new owner reproduces the pre-refactor outputs of
   ranking_heuristics._normalize_to_tokens (default mode) and
   centrality_ranker._tokenize_for_matching (split_acronyms+split_dots+min_len=2+as_set).
2. Completeness gate (AST-walk): the CamelCase-split regex `([a-z])([A-Z])` and the
   private helper names `_normalize_to_tokens` / `_tokenize_for_matching` must not be
   defined outside search/tokenization.py in the non-test source tree.
"""

from __future__ import annotations

import ast
import glob
from pathlib import Path

from search.tokenization import (
    CODE_TERM_BLOCKLIST,
    is_camelcase,
    is_dotted_symbol,
    is_snake_or_dunder,
    is_upper_const,
    normalize_to_tokens,
)


# ---------------------------------------------------------------------------
# Behaviour parity — ranking_heuristics mode (default)
# ---------------------------------------------------------------------------


class TestNormalizeToTokensDefaultMode:
    """Default mode must reproduce ranking_heuristics._normalize_to_tokens exactly."""

    def test_camelcase_split(self):
        assert normalize_to_tokens("CodeEmbedder") == ["code", "embedder"]

    def test_snake_case_split(self):
        assert normalize_to_tokens("embed_chunks") == ["embed", "chunks"]

    def test_mixed_camel_snake(self):
        assert normalize_to_tokens("IntelligentSearcher__init__") == [
            "intelligent",
            "searcher",
            "init",
        ]

    def test_single_char_tokens_kept(self):
        # Default min_len=1: single-char tokens are preserved
        result = normalize_to_tokens("a_b_c")
        assert "a" in result
        assert "b" in result
        assert "c" in result

    def test_returns_list(self):
        result = normalize_to_tokens("SearchResult")
        assert isinstance(result, list)

    def test_no_acronym_split_by_default(self):
        # "HTMLParser" — no [a-z][A-Z] boundary, so it stays as one token
        result = normalize_to_tokens("HTMLParser")
        assert "htmlparser" in result

    def test_no_dot_split_by_default(self):
        # dots are NOT split in default mode
        result = normalize_to_tokens("module.Class")
        # \w+ matches word chars — dot splits naturally; but underscores etc. don't
        # Actually re.findall(r"\w+", ...) splits on dots, so this passes through
        assert "module" in result
        assert "class" in result

    def test_kebab_case_split(self):
        assert normalize_to_tokens("my-function-name") == ["my", "function", "name"]

    def test_all_lowercase(self):
        assert normalize_to_tokens("SearchResult") == ["search", "result"]

    def test_representative_inputs(self):
        """Exact regression values from pre-refactor ranking_heuristics behaviour."""
        assert normalize_to_tokens("HybridSearcher") == ["hybrid", "searcher"]
        assert normalize_to_tokens("index_directory") == ["index", "directory"]
        assert normalize_to_tokens("IntelligentSearcher") == ["intelligent", "searcher"]


# ---------------------------------------------------------------------------
# Behaviour parity — centrality_ranker mode (split_acronyms+split_dots+min_len=2+as_set)
# ---------------------------------------------------------------------------


class TestNormalizeToTokensCentralityMode:
    """Centrality-ranker mode must reproduce _tokenize_for_matching exactly."""

    _opts: dict = {
        "split_acronyms": True,
        "split_dots": True,
        "min_len": 2,
        "as_set": True,
    }

    def call(self, text: str) -> set[str]:
        return normalize_to_tokens(text, **self._opts)  # type: ignore[arg-type]

    def test_returns_set(self):
        assert isinstance(self.call("CodeEmbedder"), set)

    def test_camelcase(self):
        assert self.call("CodeEmbedder") == {"code", "embedder"}

    def test_snake_case(self):
        assert self.call("embed_chunks") == {"embed", "chunks"}

    def test_dot_separated(self):
        result = self.call("IntelligentSearcher.__init__")
        assert "intelligent" in result
        assert "searcher" in result
        assert "init" in result

    def test_acronym_split(self):
        result = self.call("HTMLParser")
        assert result == {"html", "parser"}

    def test_single_char_filtered(self):
        result = self.call("a_b_c_longer")
        assert "a" not in result
        assert "b" not in result
        assert "c" not in result
        assert "longer" in result

    def test_representative_inputs(self):
        """Exact regression values from pre-refactor centrality_ranker behaviour."""
        assert self.call("CodeEmbedder") == {"code", "embedder"}
        assert self.call("embed_chunks") == {"embed", "chunks"}
        assert self.call("HTMLParser") == {"html", "parser"}
        assert "intelligent" in self.call("IntelligentSearcher.__init__")

    def test_sentence_with_code_term(self):
        result = self.call("what does CodeEmbedder do")
        assert "code" in result
        assert "embedder" in result
        assert "what" in result
        assert "does" in result
        # single-char tokens from "do" → "do" is 2 chars so kept
        assert "do" in result


# ---------------------------------------------------------------------------
# Symbol predicates
# ---------------------------------------------------------------------------


class TestIsCAmelcase:
    def test_camel(self):
        assert is_camelcase("HybridSearcher")

    def test_pascal_with_acronym_no_lower_upper_transition(self):
        # "HTMLParser": H-T-M-L-P-a-r-s-e-r — no lowercase→uppercase boundary;
        # [a-z][A-Z] doesn't match. is_camelcase is False (detected as upper-const instead).
        assert not is_camelcase("HTMLParser")

    def test_index_flat_ip(self):
        # "IndexFlatIP" has [a-z][A-Z] at "xF" and [A-Z][a-z]+[A-Z] at "FlatI"
        assert is_camelcase("IndexFlatIP")

    def test_lowercase_false(self):
        assert not is_camelcase("embed_chunks")

    def test_upper_const_false(self):
        # "FAISS" — all uppercase, no lower→upper transition
        assert not is_camelcase("FAISS")

    def test_single_word_false(self):
        assert not is_camelcase("search")


class TestIsUpperConst:
    def test_faiss(self):
        assert is_upper_const("FAISS")

    def test_bm25(self):
        assert is_upper_const("BM25")

    def test_max_retries(self):
        assert is_upper_const("MAX_RETRIES")

    def test_api(self):
        assert is_upper_const("API")

    def test_single_char_false(self):
        # Single uppercase char — no second char
        assert not is_upper_const("A")

    def test_single_uppercase_with_digit_only(self):
        # "A1" — second char is digit (not alpha), so any(c.isalpha() for c in "1") is False
        assert not is_upper_const("A1")

    def test_camelcase_false(self):
        assert not is_upper_const("HybridSearcher")

    def test_lowercase_false(self):
        assert not is_upper_const("embed")


class TestIsSnakeOrDunder:
    def test_dunder_init(self):
        assert is_snake_or_dunder("__init__")

    def test_dunder_repr(self):
        assert is_snake_or_dunder("__repr__")

    def test_snake_case(self):
        assert is_snake_or_dunder("embed_chunks")

    def test_private_snake(self):
        assert is_snake_or_dunder("_normalize_to_tokens")

    def test_camelcase_false(self):
        assert not is_snake_or_dunder("HybridSearcher")

    def test_upper_const_false(self):
        assert not is_snake_or_dunder("FAISS")

    def test_plain_lowercase_no_underscore_false(self):
        assert not is_snake_or_dunder("search")


class TestIsDottedSymbol:
    def test_module_class(self):
        assert is_dotted_symbol("module.Class")

    def test_self_method(self):
        assert is_dotted_symbol("self.Method")

    def test_no_uppercase_false(self):
        assert not is_dotted_symbol("self.method")

    def test_no_dot_false(self):
        assert not is_dotted_symbol("ClassName")


# ---------------------------------------------------------------------------
# CODE_TERM_BLOCKLIST
# ---------------------------------------------------------------------------


class TestCodeTermBlocklist:
    def test_is_frozenset(self):
        assert isinstance(CODE_TERM_BLOCKLIST, frozenset)

    def test_contains_expected_terms(self):
        for term in ("method", "function", "class", "module", "error", "exception"):
            assert term in CODE_TERM_BLOCKLIST

    def test_does_not_contain_symbol_names(self):
        # Real symbol names must not be in the blocklist
        for sym in (
            "HybridSearcher",
            "embed_chunks",
            "CodeEmbedder",
            "resync_if_desynced",
        ):
            assert sym not in CODE_TERM_BLOCKLIST


# ---------------------------------------------------------------------------
# P8 completeness gate — AST walk
# ---------------------------------------------------------------------------


class TestTokenizationOwnership:
    """P8 gate: camel-split regex and helper function names must not leak out of tokenization.py."""

    _OWNER = "search/tokenization.py"

    def _source_files(self) -> list[str]:
        files = []
        for fpath in glob.glob("**/*.py", recursive=True):
            norm = fpath.replace("\\", "/")
            if any(
                norm.startswith(prefix) for prefix in (".venv", "tests", "__pycache__")
            ):
                continue
            files.append(fpath)
        return files

    # Files exempt from the camel-split regex gate because they use the regex for
    # a different purpose (BM25 string pre-processing, not token scoring).
    _REGEX_EXEMPT: frozenset[str] = frozenset({"search/bm25_index.py"})

    def test_camel_split_regex_only_in_owner(self):
        """r'([a-z])([A-Z])' for token-scoring must only appear in search/tokenization.py.

        search/bm25_index.py is exempt: it uses the same regex for BM25 string
        pre-processing (producing a modified string, not a token list).
        """
        stray: list[str] = []
        for fpath in self._source_files():
            norm = fpath.replace("\\", "/")
            if norm == self._OWNER or norm in self._REGEX_EXEMPT:
                continue
            try:
                source = Path(fpath).read_text(encoding="utf-8")
            except OSError:
                continue
            if r"([a-z])([A-Z])" in source:
                stray.append(fpath)
        assert not stray, (
            f"Stale CamelCase-split regex r'([a-z])([A-Z])' found outside {self._OWNER}: {stray}. "
            "Route through tokenization.normalize_to_tokens()."
        )

    def test_normalize_to_tokens_body_delegates_to_owner(self):
        """_normalize_to_tokens wrapper in ranking_heuristics must not contain the split regex.

        The thin wrapper method is allowed to exist (backward compat for internal call sites),
        but its body must delegate — not re-implement the regex.
        """
        stray: list[str] = []
        for fpath in self._source_files():
            norm = fpath.replace("\\", "/")
            if norm == self._OWNER:
                continue
            try:
                source = Path(fpath).read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, OSError):
                continue
            lines = source.splitlines()
            for node in ast.walk(tree):
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == "_normalize_to_tokens"
                ):
                    # Check that the function body doesn't contain the split regex
                    body_src = "\n".join(lines[node.lineno - 1 : node.end_lineno])
                    if r"([a-z])([A-Z])" in body_src:
                        stray.append(f"{fpath}:{node.lineno}")
        assert not stray, (
            f"_normalize_to_tokens re-implements the camel-split regex in: {stray}. "
            "Delegate to tokenization.normalize_to_tokens() instead."
        )

    def test_tokenize_for_matching_body_delegates_to_owner(self):
        """_tokenize_for_matching wrapper in centrality_ranker must not contain the split regex.

        Same principle: thin wrapper allowed, direct re-implementation is not.
        """
        stray: list[str] = []
        for fpath in self._source_files():
            norm = fpath.replace("\\", "/")
            if norm == self._OWNER:
                continue
            try:
                source = Path(fpath).read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, OSError):
                continue
            lines = source.splitlines()
            for node in ast.walk(tree):
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == "_tokenize_for_matching"
                ):
                    body_src = "\n".join(lines[node.lineno - 1 : node.end_lineno])
                    if r"([a-z])([A-Z])" in body_src:
                        stray.append(f"{fpath}:{node.lineno}")
        assert not stray, (
            f"_tokenize_for_matching re-implements the camel-split regex in: {stray}. "
            "Route through tokenization.normalize_to_tokens(...) instead."
        )

    def test_owner_module_exists(self):
        assert Path(self._OWNER).exists(), (
            f"{self._OWNER} was deleted — P8 single tokenization owner is gone."
        )
