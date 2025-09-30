"""BM25 sparse index for text search (CPU-only)."""

import json
import logging
import pickle
import re
import string
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize

    # Download required NLTK data if needed
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt", quiet=True)

    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        nltk.download("stopwords", quiet=True)

except ImportError:
    nltk = None
    stopwords = None
    word_tokenize = None


class TextPreprocessor:
    """Handles text preprocessing for BM25 indexing."""

    def __init__(self, use_stopwords: bool = True):
        self.use_stopwords = use_stopwords
        self._stop_words = set()
        self._logger = logging.getLogger(__name__)

        if use_stopwords and stopwords:
            try:
                self._stop_words = set(stopwords.words("english"))
            except Exception as e:
                self._logger.warning(f"Could not load stopwords: {e}")
                self.use_stopwords = False

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        if not text or not isinstance(text, str):
            return []

        # Use NLTK tokenizer if available, otherwise simple split
        if word_tokenize:
            try:
                tokens = word_tokenize(text.lower())
            except Exception:
                tokens = text.lower().split()
        else:
            tokens = text.lower().split()

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


class BM25Index:
    """BM25 sparse index manager (CPU-only)."""

    def __init__(self, storage_dir: str, use_stopwords: bool = True):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self.index_path = self.storage_dir / "bm25.index"
        self.metadata_path = self.storage_dir / "bm25_metadata.json"
        self.docs_path = self.storage_dir / "bm25_docs.json"

        # Components
        self.preprocessor = TextPreprocessor(use_stopwords)
        self._bm25 = None
        self._documents = []  # Original documents
        self._doc_ids = []  # Document IDs
        self._tokenized_docs = []  # Tokenized documents
        self._metadata = {}

        self._logger = logging.getLogger(__name__)

        # Check dependencies
        self._check_dependencies()

    def _check_dependencies(self):
        """Check if required dependencies are available."""
        if BM25Okapi is None:
            raise ImportError(
                "rank-bm25 not found. Install with: pip install rank-bm25"
            )

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
        documents: List[str],
        doc_ids: List[str],
        metadata: Optional[Dict[str, Dict]] = None,
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
                # Special preprocessing for code content
                preprocessed = self.preprocessor.preprocess_code(doc)
                tokens = self.preprocessor.tokenize(preprocessed)
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
                self._bm25 = BM25Okapi(self._tokenized_docs)

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

            except Exception as bm25_error:
                self._logger.error(
                    f"[BM25_INDEX] Failed to create BM25 index: {bm25_error}"
                )
                # Reset the BM25 index to None on failure
                self._bm25 = None
                raise ValueError(f"BM25 index creation failed: {bm25_error}")

            self._logger.info(
                f"[BM25_INDEX] Successfully indexed {len(documents)} new documents (total: {self.size})"
            )

        except Exception as e:
            self._logger.error(f"[BM25_INDEX] Failed to index documents: {e}")
            raise

    def search(
        self, query: str, k: int = 5, min_score: float = 0.0
    ) -> List[Tuple[str, float, Dict]]:
        """Search for similar documents using BM25."""
        if self._bm25 is None or self.is_empty:
            self._logger.warning("BM25 index is empty")
            return []

        # Preprocess and tokenize query
        preprocessed_query = self.preprocessor.preprocess_code(query)
        query_tokens = self.preprocessor.tokenize(preprocessed_query)

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
            metadata = dict(self._metadata.get(doc_id, {}))  # Return a copy, not reference

            # Ensure content field exists - add from document store if missing
            if 'content' not in metadata and idx < len(self._documents):
                metadata['content'] = self._documents[idx]

            results.append((doc_id, score, metadata))

        self._logger.debug(
            f"BM25 search returned {len(results)} results for query: '{query}'"
        )

        return results

    def get_document_by_id(self, doc_id: str) -> Optional[str]:
        """Get original document by ID."""
        try:
            idx = self._doc_ids.index(doc_id)
            return self._documents[idx]
        except ValueError:
            return None

    def remove_documents(self, doc_ids: List[str]) -> int:
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
                self._bm25 = BM25Okapi(self._tokenized_docs)
            else:
                self._bm25 = None

            self._logger.info(f"Removed {removed_count} documents from BM25 index")

        return removed_count

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
                    self._bm25 = BM25Okapi(self._tokenized_docs)
                    self._logger.info(
                        f"[BM25_SAVE] Successfully recovered BM25 index with {len(self._tokenized_docs)} documents"
                    )
                    with open(self.index_path, "wb") as f:
                        pickle.dump(self._bm25, f)
                    self._logger.info(
                        f"[BM25_SAVE] Saved recovered index: {self.index_path.stat().st_size} bytes"
                    )
                except Exception as recovery_error:
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

            # Save metadata
            self._logger.debug(f"[BM25_SAVE] Saving metadata to {self.metadata_path}")
            metadata = {
                "size": self.size,
                "use_stopwords": self.preprocessor.use_stopwords,
                "doc_metadata": self._metadata,
            }
            with open(self.metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            self._logger.info(
                f"[BM25_SAVE] Saved metadata: {self.metadata_path.stat().st_size} bytes"
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
            with open(self.index_path, "rb") as f:
                self._bm25 = pickle.load(f)

            # Load documents
            with open(self.docs_path, "r", encoding="utf-8") as f:
                docs_data = json.load(f)
                self._documents = docs_data["documents"]
                self._doc_ids = docs_data["doc_ids"]
                self._tokenized_docs = docs_data["tokenized_docs"]

            # Load metadata
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
                self._metadata = metadata.get("doc_metadata", {})

            self._logger.info(
                f"BM25 index loaded from {self.storage_dir} with {self.size} documents"
            )
            return True

        except Exception as e:
            self._logger.error(f"Failed to load BM25 index: {e}")
            # Reset state on load failure
            self._bm25 = None
            self._documents = []
            self._doc_ids = []
            self._tokenized_docs = []
            self._metadata = {}
            return False

    def get_stats(self) -> Dict:
        """Get index statistics."""
        return {
            "total_documents": self.size,
            "has_index": self._bm25 is not None,
            "use_stopwords": self.preprocessor.use_stopwords,
            "avg_doc_length": (
                sum(len(tokens) for tokens in self._tokenized_docs)
                / len(self._tokenized_docs)
                if self._tokenized_docs
                else 0
            ),
            "vocabulary_size": (
                len(set(token for tokens in self._tokenized_docs for token in tokens))
                if self._tokenized_docs
                else 0
            ),
        }

    def remove_file_chunks(self, file_path: str, project_name: str) -> int:
        """
        Remove documents associated with a specific file.

        Args:
            file_path: Relative path of the file to remove chunks for
            project_name: Name of the project

        Returns:
            Number of documents removed
        """
        if not self._doc_ids:
            return 0

        self._logger.debug(f"Removing BM25 documents for file: {file_path}")

        # Track documents to remove
        indices_to_remove = []
        removed_count = 0

        # Find documents that belong to this file
        for i, doc_id in enumerate(self._doc_ids):
            # Check if document belongs to the file
            # Document IDs typically include file path information
            if file_path in doc_id:
                indices_to_remove.append(i)
                removed_count += 1

        if not indices_to_remove:
            return 0

        # Remove documents in reverse order to maintain indices
        for i in reversed(indices_to_remove):
            if i < len(self._documents):
                del self._documents[i]
            if i < len(self._doc_ids):
                doc_id = self._doc_ids[i]
                del self._doc_ids[i]
                # Remove from metadata if exists
                if doc_id in self._metadata:
                    del self._metadata[doc_id]
            if i < len(self._tokenized_docs):
                del self._tokenized_docs[i]

        # Rebuild BM25 index if we removed documents
        if removed_count > 0:
            try:
                if self._tokenized_docs:
                    # Only rebuild if we still have documents
                    self._bm25 = BM25Okapi(self._tokenized_docs)
                    self._logger.debug(
                        f"Rebuilt BM25 index after removing {removed_count} documents"
                    )
                else:
                    # No documents left, clear the index
                    self._bm25 = None
                    self._logger.debug("Cleared BM25 index (no documents remaining)")
            except Exception as e:
                self._logger.warning(f"Failed to rebuild BM25 index: {e}")
                # Reset to empty state on rebuild failure
                self._bm25 = None
                self._documents = []
                self._doc_ids = []
                self._tokenized_docs = []
                self._metadata = {}

        self._logger.info(
            f"Removed {removed_count} BM25 documents for file: {file_path}"
        )
        return removed_count
