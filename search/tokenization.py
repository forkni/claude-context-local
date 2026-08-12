"""Single owner for CamelCase/snake_case tokenization and code-symbol predicates.

P8 — architecture deepening: consolidates the duplicated camel/snake splitter that
existed in ranking_heuristics._normalize_to_tokens and centrality_ranker._tokenize_for_matching,
and the inline symbol-recognition regexes from intent_classifier._detect_code_symbols.

Public API
----------
normalize_to_tokens(text, *, split_acronyms, split_dots, min_len, as_set)
    Single splitting core with knobs that reproduce both pre-existing variants exactly.

tokenize_dotted_identifiers(text)
    Case-preserving, dot-preserving tokenizer shared by
    intent_classifier._detect_code_symbols and _extract_symbol_from_query.

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
# Dotted-identifier tokenizer (case-preserving, unlike normalize_to_tokens)
# ---------------------------------------------------------------------------


def tokenize_dotted_identifiers(text: str) -> list[str]:
    """Split text into word/underscore/dot runs, preserving case and dots.

    The only tokenizer in the repo that keeps ``.`` inside a token, so a
    qualified symbol like ``module.Class`` or ``self.__init__`` survives as
    one token instead of being split at the dot (contrast
    ``normalize_to_tokens``, which lowercases and can split *on* dots via
    ``split_dots``). Case is preserved so the symbol predicates below
    (``is_camelcase``, ``is_upper_const``, ``is_snake_or_dunder``,
    ``is_dotted_symbol``) can run against the original token.

    Used by ``intent_classifier._detect_code_symbols`` and
    ``_extract_symbol_from_query`` to recognize code symbols inside a query.
    """
    return re.findall(r"[\w.]+", text)


# ---------------------------------------------------------------------------
# Path/symbol augmentation text (Track D — BM25 document enrichment)
# ---------------------------------------------------------------------------


def build_path_symbol_text(relative_path: str, symbol_name: str) -> str:
    """Build a BM25 augmentation string from a chunk's file path and symbol name.

    Emits each path component and symbol segment both whole and camel/snake-split
    so the identifier-preserving ("whole") tokenizer indexes both forms: a query
    for "query cache" matches ``embeddings/query_cache.py`` chunks, while a query
    for the exact identifier ``query_cache`` still matches the whole token.

    The file extension is stripped (``.py`` adds no signal), tokens are deduped
    case-insensitively in first-seen order (term frequency of augmentation tokens
    stays 1 so code-body occurrences keep dominating BM25 TF), and single-char
    tokens are dropped.

    Args:
        relative_path: Chunk's file path relative to the project root
            (``/`` or ``\\`` separators).
        symbol_name: Qualified symbol name, e.g. ``"HybridSearcher.add_embeddings"``.

    Returns:
        Space-joined augmentation terms, e.g.
        ``"search hybrid_searcher hybrid searcher HybridSearcher add_embeddings add embeddings"``.
        Empty string if there is nothing to add.
    """
    terms: list[str] = []
    parts = [p for p in relative_path.replace("\\", "/").split("/") if p]
    for i, comp in enumerate(parts):
        if i == len(parts) - 1:
            comp = comp.rsplit(".", 1)[0]  # strip file extension
        terms.append(comp)
        terms.extend(normalize_to_tokens(comp))
    for seg in symbol_name.split("."):
        terms.append(seg)
        terms.extend(normalize_to_tokens(seg))

    seen: set[str] = set()
    out: list[str] = []
    for term in terms:
        key = term.lower()
        if len(key) < 2 or key in seen:
            continue
        seen.add(key)
        out.append(term)
    return " ".join(out)


def augment_bm25_document(chunk_id: str, content: str) -> str:
    """Append path/symbol tokens to a BM25 document (Track D, INDEX_VERSION 4).

    Chunk IDs are ``path:lines:type:name``; the path components and symbol name
    (whole + camel/snake-split forms) are appended once so identifier and
    file-name queries match chunks whose code body never repeats them.

    Applied at BM25 document-build time in BOTH indexing paths
    (``HybridSearcher.add_embeddings`` and
    ``IndexSynchronizer.resync_bm25_from_dense``) while the persisted
    ``bm25_text`` metadata stays raw — augmentation is therefore applied
    exactly once no matter how often the BM25 index is rebuilt from dense
    metadata, and a version-mismatch resync upgrades an old index without
    re-embedding.

    Gated on BM25-standalone metrics (scripts/benchmark/bm25_path_token_ab.py,
    2026-07-26): 63q MRR +0.113 / R@5 +0.081, 96q MRR +0.083 / R@5 +0.060.
    """
    parts = chunk_id.split(":")
    if len(parts) < 4:
        return content
    augmentation = build_path_symbol_text(parts[0], ":".join(parts[3:]))
    if not augmentation:
        return content
    return f"{content}\n{augmentation}" if content else augmentation


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
