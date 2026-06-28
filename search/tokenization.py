"""Single owner for CamelCase/snake_case tokenization and code-symbol predicates.

P8 — architecture deepening: consolidates the duplicated camel/snake splitter that
existed in ranking_heuristics._normalize_to_tokens and centrality_ranker._tokenize_for_matching,
and the inline symbol-recognition regexes from intent_classifier._detect_code_symbols.

Public API
----------
normalize_to_tokens(text, *, split_acronyms, split_dots, min_len, as_set)
    Single splitting core with knobs that reproduce both pre-existing variants exactly.

is_camelcase(token) / is_upper_const(token) / is_snake_or_dunder(token) / is_dotted_symbol(token)
    Case-sensitive predicates used by intent_classifier._detect_code_symbols; extracted
    verbatim so the regex lives once.

CODE_TERM_BLOCKLIST
    Public rename of intent_classifier._CODE_TERM_BLOCKLIST; still imported there.
"""

from __future__ import annotations

import re
from typing import Literal, overload


# ---------------------------------------------------------------------------
# Token splitter
# ---------------------------------------------------------------------------


@overload
def normalize_to_tokens(
    text: str,
    *,
    split_acronyms: bool = ...,
    split_dots: bool = ...,
    min_len: int = ...,
    as_set: Literal[False] = ...,
) -> list[str]: ...


@overload
def normalize_to_tokens(
    text: str,
    *,
    split_acronyms: bool = ...,
    split_dots: bool = ...,
    min_len: int = ...,
    as_set: Literal[True],
) -> set[str]: ...


def normalize_to_tokens(
    text: str,
    *,
    split_acronyms: bool = False,
    split_dots: bool = False,
    min_len: int = 1,
    as_set: bool = False,
) -> list[str] | set[str]:
    """Convert text to normalised tokens, handling CamelCase, snake_case, and kebab-case.

    Default behaviour (split_acronyms=False, split_dots=False, min_len=1, as_set=False)
    reproduces ranking_heuristics._normalize_to_tokens **exactly**::

        normalize_to_tokens("CodeEmbedder") == ["code", "embedder"]
        normalize_to_tokens("embed_chunks") == ["embed", "chunks"]

    Centrality-ranker mode (all knobs set) reproduces _tokenize_for_matching **exactly**::

        normalize_to_tokens(
            "HTMLParser.embed_chunks",
            split_acronyms=True, split_dots=True, min_len=2, as_set=True
        ) == {"html", "parser", "embed", "chunks"}

    Args:
        text: Input string.
        split_acronyms: If True, split uppercase runs before the CamelCase pass,
            e.g. ``"HTMLParser"`` → ``"HTML Parser"`` → ``{"html", "parser"}``.
            Must run *before* the ``[a-z][A-Z]`` pass (centrality_ranker order).
        split_dots: If True, replace ``.`` with space first, splitting qualified
            names like ``"module.Class"`` or ``"self.__init__"``.
        min_len: Minimum token length to keep (1 = keep all, 2 = filter single chars).
        as_set: If True, return a ``set``; otherwise return a ``list``.

    Returns:
        List or set of lowercase tokens.
    """
    if split_dots:
        text = text.replace(".", " ")
    # Split CamelCase: "CodeEmbedder" → "Code Embedder"
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    if split_acronyms:
        # Split uppercase runs: "HTMLParser" → "HTML Parser"
        # Must run after the [a-z][A-Z] split to avoid double-splitting.
        text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
    # Split snake_case and kebab-case
    text = text.replace("_", " ").replace("-", " ")
    tokens = re.findall(r"\w+", text.lower())
    if min_len > 1:
        tokens = [t for t in tokens if len(t) >= min_len]
    if as_set:
        return set(tokens)
    return tokens


# ---------------------------------------------------------------------------
# Symbol predicates (extracted verbatim from intent_classifier._detect_code_symbols)
# These run on the ORIGINAL (non-lowercased) token — they are case-sensitive.
# ---------------------------------------------------------------------------


def is_camelcase(token: str) -> bool:
    """CamelCase/PascalCase: HybridSearcher, IndexFlatIP, HTMLParser.

    Matches a lowercase→uppercase transition *or* an upper-lower-upper run.
    """
    return bool(
        re.search(r"[a-z][A-Z]", token) or re.search(r"[A-Z][a-z]+[A-Z]", token)
    )


def is_upper_const(token: str) -> bool:
    """UPPER_CASE constants with 2+ alpha chars: FAISS, BM25, MAX_RETRIES.

    Requires the token to start with an uppercase letter followed by at least
    one more uppercase-or-digit-or-underscore character, *and* contain a second
    alpha character (excludes lone uppercase letters like ``"I"`` or ``"A"``).
    """
    return bool(
        re.match(r"^[A-Z][A-Z0-9_]{1,}$", token) and any(c.isalpha() for c in token[1:])
    )


def is_snake_or_dunder(token: str) -> bool:
    """snake_case identifiers and dunder methods: embed_chunks, __init__, __repr__.

    Matches:
    - ``__word__``  (dunder, via first branch)
    - ``_?[a-z][a-z0-9_]+``  (snake_case, optional leading underscore)
    """
    return bool(
        re.match(r"^__[a-z]\w+__$", token)
        or "_" in token
        and re.match(r"^_?[a-z][a-z0-9_]+$", token)
    )


def is_dotted_symbol(token: str) -> bool:
    """dot.notation containing an uppercase letter: module.Class, self.Method."""
    return "." in token and bool(re.search(r"[A-Z]", token))


# ---------------------------------------------------------------------------
# Shared blocklist (public rename of intent_classifier._CODE_TERM_BLOCKLIST)
# ---------------------------------------------------------------------------

CODE_TERM_BLOCKLIST: frozenset[str] = frozenset(
    {
        "method",
        "function",
        "class",
        "module",
        "variable",
        "constant",
        "attribute",
        "property",
        "field",
        "parameter",
        "argument",
        "type",
        "interface",
        "enum",
        "struct",
        "trait",
        "protocol",
        "caller",
        "callers",
        "callee",
        "callees",
        "implementation",
        "definition",
        "declaration",
        "reference",
        "import",
        "imports",
        "export",
        "exports",
        "handler",
        "helper",
        "utility",
        "wrapper",
        "factory",
        "object",
        "instance",
        "value",
        "result",
        "error",
        "exception",
    }
)
