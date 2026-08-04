"""BM25 sparse index for text search (CPU-only)."""

import json
import logging
import pickle
import re
import shutil
import string
from collections import OrderedDict
from pathlib import Path
from typing import Any

from utils.path_utils import normalize_path, path_matches


try:
    from rank_bm25 import BM25Okapi
except ImportError as e:
    raise ImportError(
        "rank_bm25 package is required for BM25 search. "
        "Install with: pip install rank_bm25"
    ) from e

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem.snowball import SnowballStemmer
    from nltk.tokenize import word_tokenize

    # word_tokenize needs tokenizers/punkt_tab; TextPreprocessor probes for
    # that once at init and falls back to str.split when it's missing (see
    # _resolve_tokenizer), so only stopwords need downloading here.
    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        nltk.download("stopwords", quiet=True)

except ImportError:
    nltk = None
    stopwords = None
    word_tokenize = None
    SnowballStemmer = None


class TextPreprocessor:
    """Handles text preprocessing for BM25 indexing.

    Supports:
    - NLTK word tokenization
    - Stopword filtering
    - Snowball stemming (Porter2 algorithm)
    - Code-specific preprocessing (camelCase/snake_case splitting)

    Tokenizer variants (arXiv 2605.18561 — BM25 code tokenization):
    - "legacy": destructive camelCase/snake_case splitting via preprocess_code,
      then word tokenization + optional stemming (parts-only; the whole
      identifier is never a token).
    - "whole": identifiers kept whole (lowercased, underscores preserved);
      no destructive split, no stemming (T1 in the paper).
    - "additive": whole identifiers PLUS their camel/snake sub-tokens, so
      both `get_user_name` and `get`/`user`/`name` are index terms (T2).
    """

    TOKENIZER_VARIANTS = ("legacy", "whole", "additive")

    # Identifier-preserving token extraction: identifiers (incl. underscores)
    # or bare number runs. Used by the "whole"/"additive" variants.
    _IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+")

    # Bounded LRU cap for the stemmer memo (see _stem_token). This project's
    # corpus has ~18k distinct tokens today; the cap leaves headroom for
    # corpus growth while still bounding worst-case memory.
    _STEM_CACHE_MAX_SIZE = 50_000

    def __init__(
        self,
        use_stopwords: bool = True,
        use_stemming: bool = True,
        tokenizer: str = "legacy",
    ) -> None:
        """Initialize text preprocessor.

        Args:
            use_stopwords: Whether to filter English stopwords
            use_stemming: Whether to apply Snowball stemming for word normalization
                (only honored by the "legacy" tokenizer; "whole"/"additive"
                never stem — stemming corrupts code identifiers)
            tokenizer: Tokenizer variant — one of TOKENIZER_VARIANTS
        """
        if tokenizer not in self.TOKENIZER_VARIANTS:
            raise ValueError(
                f"Unknown tokenizer {tokenizer!r}, expected one of "
                f"{self.TOKENIZER_VARIANTS}"
            )
        self.tokenizer = tokenizer
        self.use_stopwords = use_stopwords
        self.use_stemming = use_stemming
        self._stop_words = set()
        self._stemmer = None
        self._stem_cache: OrderedDict[str, str] = OrderedDict()
        self._logger = logging.getLogger(__name__)

        # Initialize stopwords
        if use_stopwords and stopwords:
            try:
                self._stop_words = set(stopwords.words("english"))
            except (LookupError, OSError) as e:
                self._logger.warning(f"Could not load stopwords: {e}")
                self.use_stopwords = False

        # Initialize stemmer
        if use_stemming and SnowballStemmer:
            try:
                self._stemmer = SnowballStemmer("english")
                self._logger.debug("Snowball stemmer initialized")
            except (LookupError, OSError) as e:
                self._logger.warning(f"Could not initialize stemmer: {e}")
                self.use_stemming = False

        # Probe word_tokenize once here rather than per-document in tokenize():
        # it raises LookupError/RuntimeError when tokenizers/punkt_tab isn't
        # installed, and every document would otherwise pay that exception cost.
        self._tokenize_words = self._resolve_tokenizer()

    def _resolve_tokenizer(self):
        """Return the working word-tokenizer callable, probed once.

        Falls back to str.split (bound the same way word_tokenize is used:
        called with a single lowercased string, returning a list of tokens)
        when NLTK's tokenizer data isn't available.
        """
        if word_tokenize is None:
            return str.split
        try:
            word_tokenize("probe")
        except (LookupError, RuntimeError):
            return str.split
        return word_tokenize

    def _stem_token(self, token: str) -> str:
        """Stem a single token, memoized via a bounded LRU cache.

        SnowballStemmer.stem() is a pure function of its input, and the
        corpus re-stems the same tokens repeatedly (16x+ redundancy measured
        on this project's own corpus) — caching avoids redundant stem()
        calls across documents. Mirrors the OrderedDict + move_to_end LRU
        idiom used by QueryEmbeddingCache/ChunkEmbeddingCache.
        """
        if self._stemmer is None:
            return token
        cached = self._stem_cache.get(token)
        if cached is not None:
            self._stem_cache.move_to_end(token)
            return cached
        stemmed = self._stemmer.stem(token)
        if len(self._stem_cache) >= self._STEM_CACHE_MAX_SIZE:
            self._stem_cache.popitem(last=False)
        self._stem_cache[token] = stemmed
        return stemmed

    def tokenize(self, text: str) -> list[str]:
        """Tokenize text into words with optional stemming.

        Process:
        1. Lowercase and tokenize (NLTK word_tokenize or split)
        2. Clean tokens (remove punctuation, keep code-friendly chars)
        3. Filter stopwords (if enabled)
        4. Apply stemming (if enabled)

        Args:
            text: Input text to tokenize

        Returns:
            List of processed tokens
        """
        if not text or not isinstance(text, str):
            return []

        tokens = self._tokenize_words(text.lower())

        # Remove punctuation and filter tokens
        tokens = [
            self._clean_token(token)
            for token in tokens
            if token and not token.isspace()
        ]

        # Filter out empty tokens and stopwords
        tokens = [
            token
            for token in tokens
            if token and (not self.use_stopwords or token not in self._stop_words)
        ]

        # Apply stemming (normalize word forms: indexing→index, managed→manag)
        if self.use_stemming and self._stemmer:
            try:
                tokens = [self._stem_token(token) for token in tokens]
            except (ValueError, TypeError) as e:
                self._logger.warning(f"Stemming failed, using original tokens: {e}")

        return tokens

    def _clean_token(self, token: str) -> str:
        """Clean a token by removing punctuation and normalizing."""
        # Remove punctuation from start and end
        token = token.strip(string.punctuation)

        # Keep alphanumeric and some special chars (useful for code)
        token = re.sub(r"[^\w\-\._]", "", token)

        # Remove if too short (but keep single letters for code variables)
        if len(token) < 1:
            return ""

        return token

    def preprocess_code(self, code: str) -> str:
        """Special preprocessing for code content."""
        if not code:
            return ""

        # Split camelCase and snake_case identifiers
        code = re.sub(r"([a-z])([A-Z])", r"\1 \2", code)
        code = code.replace("_", " ")

        # Add spaces around operators for better tokenization
        operators = ["==", "!=", "<=", ">=", "&&", "||", "->", "=>", "::"]
        for op in operators:
            code = code.replace(op, f" {op} ")

        return code

    def _tokenize_identifiers(self, text: str, *, additive: bool) -> list[str]:
        """Identifier-preserving tokenization ("whole"/"additive" variants).

        Extracts identifiers and numbers, lowercases them but keeps them
        intact (`getUserName` → `getusername`, `get_user_name` unchanged).
        In additive mode, multi-part identifiers additionally emit their
        camel/snake sub-tokens via normalize_to_tokens — whole AND parts,
        never parts-only. No stemming in either mode.
        """
        from search.tokenization import normalize_to_tokens

        tokens: list[str] = []
        for raw in self._IDENTIFIER_RE.findall(text):
            tokens.append(raw.lower())
            if additive:
                parts = normalize_to_tokens(raw, split_acronyms=True)
                if len(parts) > 1:
                    tokens.extend(parts)
        if self.use_stopwords:
            tokens = [t for t in tokens if t not in self._stop_words]
        return tokens

    def process(self, text: str) -> list[str]:
        """Preprocess and tokenize `text` per the configured tokenizer variant.

        Single entry point used for both index-time documents and query
        strings, guaranteeing index/query tokenization always match.
        """
        if not text or not isinstance(text, str):
            return []
        if self.tokenizer == "whole":
            return self._tokenize_identifiers(text, additive=False)
        if self.tokenizer == "additive":
            return self._tokenize_identifiers(text, additive=True)
        return self.tokenize(self.preprocess_code(text))


class BM25Index:
    """BM25 sparse index manager (CPU-only)."""

    # Index version for compatibility tracking
    # Version 2: Added stemming support
    # Version 3: Tokenizer variants (bm25_tokenizer knob, default "whole")
    # Version 4: Path/symbol token augmentation of BM25 documents (Track D)
    INDEX_VERSION = 4

    def __init__(
        self,
        storage_dir: str,
        use_stopwords: bool = True,
        use_stemming: bool = True,
        tokenizer: str = "legacy",
        k1: float = 1.5,
        b: float = 0.75,
    ):
        """Initialize BM25 index.

        Args:
            storage_dir: Directory to store index files
            use_stopwords: Whether to filter stopwords
            use_stemming: Whether to apply Snowball stemming (default: True;
                ignored by the "whole"/"additive" tokenizer variants)
            tokenizer: Tokenizer variant (see TextPreprocessor.TOKENIZER_VARIANTS)
            k1: Okapi BM25 term-frequency saturation parameter
            b: Okapi BM25 document-length normalization parameter
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self.index_path = self.storage_dir / "bm25.index"
        self.metadata_path = self.storage_dir / "bm25_metadata.json"
        self.docs_path = self.storage_dir / "bm25_docs.json"

        # Store configuration for version tracking
        self.use_stopwords = use_stopwords
        self.use_stemming = use_stemming
        self.tokenizer = tokenizer
        self.k1 = k1
        self.b = b

        # Components
        self.preprocessor = TextPreprocessor(use_stopwords, use_stemming, tokenizer)
        self._bm25 = None
        self._documents = []  # Original documents
        self._doc_ids = []  # Document IDs
        self._tokenized_docs = []  # Tokenized documents
        self._metadata = {}

        self._logger = logging.getLogger(__name__)

        # Check dependencies
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Check if required dependencies are available.

        Raises:
            ImportError: If rank-bm25 is not installed.
        """
        if nltk is None:
            self._logger.warning(
                "NLTK not found. Using basic tokenization. "
                "Install with: pip install nltk"
            )

    @property
    def is_empty(self) -> bool:
        """Check if index is empty."""
        return len(self._documents) == 0

    @property
    def size(self) -> int:
        """Get number of indexed documents."""
        return len(self._documents)

    def index_documents(
        self,
        documents: list[str],
        doc_ids: list[str],
        metadata: dict[str, dict] | None = None,
    ) -> None:
        """Index a list of documents with their IDs."""
        if len(documents) != len(doc_ids):
            raise ValueError("Number of documents must match number of IDs")

        self._logger.info(
            f"[BM25_INDEX] index_documents called with {len(documents)} docs"
        )

        if not documents:
            self._logger.error("[BM25_INDEX] No documents provided!")
            return

        try:
            # Store documents and IDs
            self._logger.debug("[BM25_INDEX] Storing documents and IDs")
            self._documents.extend(documents)
            self._doc_ids.extend(doc_ids)

            # Store metadata if provided
            if metadata:
                self._logger.debug(
                    f"[BM25_INDEX] Storing metadata for {len(metadata)} documents"
                )

                # Store metadata with deep copy to avoid reference issues
                for doc_id, meta in metadata.items():
                    self._metadata[doc_id] = dict(meta)

            # Preprocess and tokenize documents
            self._logger.debug(f"[BM25_INDEX] Tokenizing {len(documents)} documents")
            new_tokenized = []
            for i, doc in enumerate(documents):
                # Variant-aware preprocessing + tokenization for code content
                tokens = self.preprocessor.process(doc)
                new_tokenized.append(tokens)

                if i % 100 == 0 and i > 0:
                    self._logger.debug(
                        f"[BM25_INDEX] Tokenized {i}/{len(documents)} documents"
                    )

            self._tokenized_docs.extend(new_tokenized)

            # Create/update BM25 index
            self._logger.debug("[BM25_INDEX] Creating BM25Okapi index")

            # Validate tokenized documents before creating index
            if not self._tokenized_docs or all(not doc for doc in self._tokenized_docs):
                raise ValueError("[BM25_INDEX] All tokenized documents are empty")

            try:
                self._bm25 = BM25Okapi(self._tokenized_docs, k1=self.k1, b=self.b)

                # Verify the BM25 index was created successfully
                if self._bm25 is None:
                    raise ValueError("[BM25_INDEX] BM25Okapi returned None")

                # Log successful creation with details
                self._logger.info(
                    f"[BM25_INDEX] BM25 index created successfully with {len(self._tokenized_docs)} total documents"
                )
                self._logger.debug(
                    f"[BM25_INDEX] BM25 index type: {type(self._bm25).__name__}"
                )

            except (ValueError, TypeError) as bm25_error:
                self._logger.error(
                    f"[BM25_INDEX] Failed to create BM25 index: {bm25_error}"
                )
                # Reset the BM25 index to None on failure
                self._bm25 = None
                raise ValueError(
                    f"BM25 index creation failed: {bm25_error}"
                ) from bm25_error

            self._logger.info(
                f"[BM25_INDEX] Successfully indexed {len(documents)} new documents (total: {self.size})"
            )

        except Exception as e:
            self._logger.error(f"[BM25_INDEX] Failed to index documents: {e}")
            raise

    def clear(self) -> None:
        """Clear the index in place, resetting to a fresh, empty state.

        Resets every mutable corpus field that init/load-failure/remove-
        failure already reset together (``_bm25``, ``_documents``,
        ``_doc_ids``, ``_tokenized_docs``, ``_metadata``) and recreates the
        on-disk storage directory. Configuration fields (``storage_dir``,
        ``tokenizer``, ``k1``, ``b``, ...) are untouched -- callers that used
        to construct a fresh ``BM25Index(**same_config)`` get identical
        state from this instead, per ADR-0025's index-identity invariant.
        """
        self._bm25 = None
        self._documents = []
        self._doc_ids = []
        self._tokenized_docs = []
        self._metadata = {}

        if self.storage_dir.exists():
            shutil.rmtree(self.storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._logger.info("BM25 index cleared")

    def search(
        self, query: str, k: int = 5, min_score: float = 0.0
    ) -> list[tuple[str, float, dict]]:
        """Search for similar documents using BM25."""
        if self._bm25 is None or self.is_empty:
            self._logger.warning("BM25 index is empty")
            return []

        # Preprocess and tokenize query (must match index-time tokenization)
        query_tokens = self.preprocessor.process(query)

        if not query_tokens:
            self._logger.warning("Query tokenized to empty list")
            return []

        # Get BM25 scores
        scores = self._bm25.get_scores(query_tokens)

        # Get top-k results
        top_indices = scores.argsort()[-k:][::-1]

        results = []
        for idx in top_indices:
            score = float(scores[idx])

            # Skip results below minimum score
            if score < min_score:
                continue

            doc_id = self._doc_ids[idx]
            metadata = dict(
                self._metadata.get(doc_id, {})
            )  # Return a copy, not reference

            # Ensure content field exists - add from document store if missing
            if "content" not in metadata and idx < len(self._documents):
                metadata["content"] = self._documents[idx]

            results.append((doc_id, score, metadata))

        self._logger.debug(
            f"BM25 search returned {len(results)} results for query: '{query}'"
        )

        return results

    def get_document_by_id(self, doc_id: str) -> str | None:
        """Get original document by ID."""
        try:
            idx = self._doc_ids.index(doc_id)
            return self._documents[idx]
        except ValueError:
            return None

    def remove_documents(self, doc_ids: list[str]) -> int:
        """Remove documents from index by their IDs."""
        removed_count = 0
        indices_to_remove = []

        # Find indices of documents to remove
        for doc_id in doc_ids:
            try:
                idx = self._doc_ids.index(doc_id)
                indices_to_remove.append(idx)
            except ValueError:
                self._logger.warning(f"Document ID not found: {doc_id}")

        # Remove in reverse order to maintain indices
        for idx in sorted(indices_to_remove, reverse=True):
            self._documents.pop(idx)
            self._doc_ids.pop(idx)
            self._tokenized_docs.pop(idx)
            removed_count += 1

        # Remove from metadata
        for doc_id in doc_ids:
            self._metadata.pop(doc_id, None)

        # Rebuild BM25 index if we removed anything
        if removed_count > 0:
            if self._tokenized_docs:
                self._bm25 = BM25Okapi(self._tokenized_docs, k1=self.k1, b=self.b)
            else:
                self._bm25 = None

            self._logger.info(f"Removed {removed_count} documents from BM25 index")

        return removed_count

    def validate_index_consistency(self) -> tuple[bool, list[str]]:
        """Validate consistency between BM25 index components.

        This method checks for:
        1. All data structures have the same length
        2. BM25 index is initialized if documents exist
        3. All doc_ids have corresponding metadata entries

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Get sizes
        doc_ids_size = len(self._doc_ids)
        documents_size = len(self._documents)
        tokenized_docs_size = len(self._tokenized_docs)
        metadata_size = len(self._metadata)

        # Check 1: All lists have same length
        if doc_ids_size != documents_size:
            issues.append(
                f"doc_ids length ({doc_ids_size}) != documents length ({documents_size})"
            )

        if doc_ids_size != tokenized_docs_size:
            issues.append(
                f"doc_ids length ({doc_ids_size}) != tokenized_docs length ({tokenized_docs_size})"
            )

        # Check 2: BM25 index exists if we have documents
        if tokenized_docs_size > 0 and self._bm25 is None:
            issues.append(
                f"BM25 index is None but have {tokenized_docs_size} tokenized documents"
            )

        # Check 3: All doc_ids have metadata (if metadata is being used)
        missing_metadata = []
        for doc_id in self._doc_ids:
            if doc_id not in self._metadata:
                missing_metadata.append(doc_id)

        if missing_metadata:
            issues.append(
                f"Missing metadata for {len(missing_metadata)} documents: "
                f"{', '.join(missing_metadata[:5])}"
                + (
                    f" ... and {len(missing_metadata) - 5} more"
                    if len(missing_metadata) > 5
                    else ""
                )
            )

        is_valid = len(issues) == 0

        if is_valid:
            self._logger.info(
                f"BM25 index consistency validated: {doc_ids_size} documents, "
                f"{metadata_size} metadata entries"
            )
        else:
            self._logger.warning(
                f"BM25 index consistency validation failed with {len(issues)} issues"
            )
            for issue in issues:
                self._logger.warning(f"  - {issue}")

        return is_valid, issues

    def save(self) -> None:
        """Save index to disk."""
        self._logger.info(f"[BM25_SAVE] Starting save to {self.storage_dir}")

        # Create directory
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._logger.debug(
            f"[BM25_SAVE] Directory created/verified: {self.storage_dir}"
        )

        try:
            # Save BM25 index - attempt recovery if None but documents exist
            if self._bm25 is not None:
                self._logger.debug(
                    f"[BM25_SAVE] Saving BM25 index to {self.index_path}"
                )
                with open(self.index_path, "wb") as f:
                    pickle.dump(self._bm25, f)
                self._logger.info(
                    f"[BM25_SAVE] Saved index: {self.index_path.stat().st_size} bytes"
                )
            elif self._tokenized_docs:
                # Attempt to recover BM25 index from tokenized documents
                self._logger.warning(
                    "[BM25_SAVE] BM25 index is None but documents exist, attempting recovery..."
                )
                try:
                    self._bm25 = BM25Okapi(self._tokenized_docs, k1=self.k1, b=self.b)
                    self._logger.info(
                        f"[BM25_SAVE] Successfully recovered BM25 index with {len(self._tokenized_docs)} documents"
                    )
                    with open(self.index_path, "wb") as f:
                        pickle.dump(self._bm25, f)
                    self._logger.info(
                        f"[BM25_SAVE] Saved recovered index: {self.index_path.stat().st_size} bytes"
                    )
                except Exception as recovery_error:  # noqa: BLE001 - resilience: BM25 recovery best-effort, save skipped on failure
                    self._logger.error(
                        f"[BM25_SAVE] Failed to recover BM25 index: {recovery_error}"
                    )
                    self._logger.warning(
                        "[BM25_SAVE] Skipping BM25 index save - could not create or recover index"
                    )
            else:
                self._logger.warning(
                    "[BM25_SAVE] No BM25 index to save (self._bm25 is None and no documents)"
                )

            # Save documents
            self._logger.debug(f"[BM25_SAVE] Saving documents to {self.docs_path}")
            docs_data = {
                "documents": self._documents,
                "doc_ids": self._doc_ids,
                "tokenized_docs": self._tokenized_docs,
            }
            with open(self.docs_path, "w", encoding="utf-8") as f:
                json.dump(docs_data, f, ensure_ascii=False, indent=2)
            self._logger.info(
                f"[BM25_SAVE] Saved docs: {self.docs_path.stat().st_size} bytes"
            )

            # Save metadata with version tracking
            self._logger.debug(f"[BM25_SAVE] Saving metadata to {self.metadata_path}")
            metadata = {
                "index_version": self.INDEX_VERSION,
                "size": self.size,
                "use_stopwords": self.use_stopwords,
                "use_stemming": self.use_stemming,
                "tokenizer": self.tokenizer,
                "k1": self.k1,
                "b": self.b,
                "doc_metadata": self._metadata,
            }
            with open(self.metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            self._logger.info(
                f"[BM25_SAVE] Saved metadata: {self.metadata_path.stat().st_size} bytes "
                f"(version={self.INDEX_VERSION}, stemming={self.use_stemming})"
            )

            self._logger.info("[BM25_SAVE] All files saved successfully")

        except Exception as e:
            self._logger.error(f"[BM25_SAVE] Failed to save: {e}")
            raise

    def load(self) -> bool:
        """Load index from disk."""
        try:
            # Check if files exist
            if not (
                self.index_path.exists()
                and self.docs_path.exists()
                and self.metadata_path.exists()
            ):
                self._logger.info("No existing BM25 index found")
                return False

            # Load BM25 index
            # SECURITY: pickle.load is safe here — index_path lives under
            # ~/.claude_code_search/ which is exclusively written by this process.
            with open(self.index_path, "rb") as f:
                self._bm25 = pickle.load(f)

            # Load documents
            with open(self.docs_path, encoding="utf-8") as f:
                docs_data = json.load(f)
                self._documents = docs_data["documents"]
                self._doc_ids = docs_data["doc_ids"]
                self._tokenized_docs = docs_data["tokenized_docs"]

            # Load metadata and check version compatibility
            with open(self.metadata_path, encoding="utf-8") as f:
                metadata = json.load(f)
                self._metadata = metadata.get("doc_metadata", {})

                # Check index version and configuration
                index_version = metadata.get(
                    "index_version", 1
                )  # Default to v1 for old indices
                saved_stemming = metadata.get(
                    "use_stemming", False
                )  # Old indices don't have stemming
                saved_stopwords = metadata.get("use_stopwords", True)
                saved_tokenizer = metadata.get(
                    "tokenizer", "legacy"
                )  # Pre-tokenizer-knob indices are all legacy

                # Detect configuration mismatch
                if index_version != self.INDEX_VERSION:
                    self._logger.warning(
                        f"⚠️  BM25 index version mismatch: on-disk v{index_version}, "
                        f"current v{self.INDEX_VERSION}.\n"
                        f"   Re-index the project to rebuild with the current format."
                    )

                if saved_tokenizer != self.tokenizer:
                    self._logger.warning(
                        f"⚠️  BM25 tokenizer mismatch detected!\n"
                        f"   Index built with tokenizer={saved_tokenizer!r}, current config={self.tokenizer!r}\n"
                        f"   Query and index tokenization will diverge — search quality WILL be degraded.\n"
                        f"   Re-index the project to rebuild with the configured tokenizer."
                    )

                if saved_stemming != self.use_stemming:
                    self._logger.warning(
                        f"⚠️  BM25 index configuration mismatch detected!\n"
                        f"   Index built with stemming={saved_stemming}, current config={self.use_stemming}\n"
                        f"   Search quality may be degraded. Recommendation: Re-index project for optimal results.\n"
                        f"   Run: 'Re-index Existing Project (Incremental)' from start_mcp_server.bat"
                    )

                if saved_stopwords != self.use_stopwords:
                    self._logger.warning(
                        f"⚠️  Stopwords config mismatch: index={saved_stopwords}, current={self.use_stopwords}"
                    )

                # k1/b are query-time scoring parameters — unlike tokenizer
                # settings they can be changed without re-indexing, so the
                # configured values are applied to the unpickled index rather
                # than warned about.
                saved_k1 = metadata.get("k1", 1.5)
                saved_b = metadata.get("b", 0.75)
                if saved_k1 != self.k1 or saved_b != self.b:
                    self._logger.info(
                        f"Applying configured BM25 params k1={self.k1}, b={self.b} "
                        f"to loaded index (saved with k1={saved_k1}, b={saved_b}; "
                        f"no re-index needed)"
                    )

            if self._bm25 is not None:
                self._bm25.k1 = self.k1
                self._bm25.b = self.b

            self._logger.info(
                f"BM25 index loaded from {self.storage_dir} with {self.size} documents "
                f"(version={index_version}, stemming={saved_stemming})"
            )
            return True

        except (OSError, ValueError) as e:
            self._logger.error(f"Failed to load BM25 index: {e}", exc_info=True)
            # Reset state on load failure
            self._bm25 = None
            self._documents = []
            self._doc_ids = []
            self._tokenized_docs = []
            self._metadata = {}
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get index statistics."""
        return {
            "total_documents": self.size,
            "has_index": self._bm25 is not None,
            "use_stopwords": self.preprocessor.use_stopwords,
            "tokenizer": self.preprocessor.tokenizer,
            "avg_doc_length": (
                sum(len(tokens) for tokens in self._tokenized_docs)
                / len(self._tokenized_docs)
                if self._tokenized_docs
                else 0
            ),
            "vocabulary_size": (
                len({token for tokens in self._tokenized_docs for token in tokens})
                if self._tokenized_docs
                else 0
            ),
        }

    def remove_files(
        self, file_paths: set[str], project_name: str | None = None
    ) -> int:
        """Remove documents associated with one or more files in a single pass.

        Args:
            file_paths: Set of file paths to remove (relative or absolute).
            project_name: Unused; kept for interface parity with other index levels.

        Returns:
            Number of documents removed.
        """
        if not self._doc_ids or not file_paths:
            return 0

        self._logger.info(
            f"[BM25_REMOVE] Checking {len(file_paths)} files against {len(self._doc_ids)} docs"
        )

        normalized_targets = {normalize_path(fp) for fp in file_paths}

        # Single pass: extract file-path portion of each doc_id and exact-match
        indices_to_remove_set = set()
        for i, doc_id in enumerate(self._doc_ids):
            file_part = doc_id.split(":", 1)[0]
            if path_matches(file_part, normalized_targets):
                indices_to_remove_set.add(i)

        if not indices_to_remove_set:
            self._logger.info("No BM25 documents found to remove")
            return 0

        removed_count = len(indices_to_remove_set)
        self._logger.info(
            f"Removing {removed_count} BM25 documents from {len(file_paths)} files"
        )

        try:
            new_documents = []
            new_doc_ids = []
            new_tokenized_docs = []
            docs_to_remove_from_metadata = []

            for i, doc_id in enumerate(self._doc_ids):
                if i not in indices_to_remove_set:
                    if i < len(self._documents):
                        new_documents.append(self._documents[i])
                    new_doc_ids.append(doc_id)
                    if i < len(self._tokenized_docs):
                        new_tokenized_docs.append(self._tokenized_docs[i])
                else:
                    docs_to_remove_from_metadata.append(doc_id)

            self._documents = new_documents
            self._doc_ids = new_doc_ids
            self._tokenized_docs = new_tokenized_docs

            for doc_id in docs_to_remove_from_metadata:
                if doc_id in self._metadata:
                    del self._metadata[doc_id]

            if self._tokenized_docs:
                self._bm25 = BM25Okapi(self._tokenized_docs, k1=self.k1, b=self.b)
                self._logger.info(
                    f"Rebuilt BM25 index: {len(self._tokenized_docs)} documents "
                    f"(removed {removed_count})"
                )
            else:
                self._bm25 = None
                self._logger.info("Cleared BM25 index (no documents remaining)")

            return removed_count

        except Exception as e:
            self._logger.error(f"Failed to batch remove BM25 documents: {e}")
            import traceback

            self._logger.error(traceback.format_exc())
            self._logger.warning(
                "BM25 batch removal failed, clearing index to prevent corruption"
            )
            self._bm25 = None
            self._documents = []
            self._doc_ids = []
            self._tokenized_docs = []
            self._metadata = {}
            raise
