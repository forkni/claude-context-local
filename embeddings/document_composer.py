"""Embedding-document composition: what text represents a chunk.

Extracted from ``CodeEmbedder`` (architecture review, candidate 6): this
cluster decides the string handed to ``model.encode()`` and is model-free by
construction — zero references to ``self.model``, ``device``, ``torch``, or
any tokenizer. `EmbeddingDocumentComposer` owns three mtime-keyed caches
(file content, import context, class signature) that collapse
O(chunks x filesize) I/O to O(files) within a pass; instance scoping bounds
the "same-tick rewrite" mtime hazard (a rewrite that lands within the OS
clock's resolution can leave ``st_mtime`` unchanged — see
``test_document_composer.py``) to one composer instead of leaking it across
callers or tests.

``EmbeddingDocumentPolicy`` is the read-only snapshot of the five
``search.config.EmbeddingConfig`` fields that govern composition — the
counterpart to ``search.rerank_window_policy.RerankWindowPolicy`` on the
reranking side. ``CodeEmbedder.create_embedding_content`` fetches the live
config and builds the policy; this module never calls ``get_search_config()``
itself.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from chunking.python_ast_chunker import CodeChunk
from search.config import EmbeddingConfig


if TYPE_CHECKING:  # pragma: no mutate
    from search.config import SearchConfig


@dataclass(frozen=True)
class EmbeddingDocumentPolicy:
    """The five ``EmbeddingConfig`` fields that govern document composition.

    Field names are byte-identical to ``search.config.EmbeddingConfig``'s so
    ``from_config`` is a plain attribute copy, not a translation.

    Defaults are read off ``EmbeddingConfig`` itself (a plain ``@dataclass``
    with no ``__post_init__``, so its class attributes already are the
    defaulted ints/bools) rather than duplicated as literals here — the two
    can drift no further apart than a single source of truth allows.
    """

    enable_import_context: bool = EmbeddingConfig.enable_import_context
    enable_class_context: bool = EmbeddingConfig.enable_class_context
    max_import_lines: int = EmbeddingConfig.max_import_lines
    max_class_signature_lines: int = EmbeddingConfig.max_class_signature_lines
    enable_structural_header: bool = EmbeddingConfig.enable_structural_header

    @classmethod
    def from_config(cls, config: SearchConfig) -> EmbeddingDocumentPolicy:
        """Build a policy from a live ``SearchConfig``.

        No try/except here — a malformed config must raise. Callers wanting a
        degraded-path fallback (e.g. ``CodeEmbedder.create_embedding_content``)
        catch the exception themselves and fall back to the defaults above.
        """
        return cls(
            enable_import_context=config.embedding.enable_import_context,
            enable_class_context=config.embedding.enable_class_context,
            max_import_lines=config.embedding.max_import_lines,
            max_class_signature_lines=config.embedding.max_class_signature_lines,
            enable_structural_header=config.embedding.enable_structural_header,
        )


class EmbeddingDocumentComposer:
    """Assembles the text handed to ``model.encode()`` for one code chunk.

    Model-free by construction. Owns three mtime-keyed caches that make a
    file with N chunks cost O(1) file reads / derived-result computations
    instead of O(N) — see ``_read_source_cached``, ``_extract_import_context``,
    ``_get_class_signature``.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

        # File-content cache for _get_class_signature (#50).
        # Avoids O(chunks × filesize) repeated re-reads when many methods share a file.
        # Maps file_path → (mtime, full_file_content); invalidated on mtime change.
        self._class_file_cache: dict[str, tuple[float, str]] = {}
        # Derived-result caches for _extract_import_context (I2) and
        # _get_class_signature (I2b): the splitlines()/regex work over
        # _class_file_cache's cached content is itself identical per file
        # (import context) or per (file, parent class) (class signature) across
        # every chunk that shares it — memoizing collapses O(chunks) redundant
        # CPU to O(files) / O(classes). Invalidated on mtime change, same as
        # _class_file_cache.
        self._import_ctx_cache: dict[str, tuple[float | None, int, str]] = {}
        self._class_sig_cache: dict[tuple[str, str], tuple[float | None, int, str]] = {}

    def clear_caches(self) -> None:
        """Drop all cached file reads / derived results. Callers: tests that
        mutate a file mid-run and CodeEmbedder.cleanup() (see that method's
        docstring for the deferred process-lifetime-growth caveat)."""
        self._class_file_cache.clear()
        self._import_ctx_cache.clear()
        self._class_sig_cache.clear()

    def _read_source_cached(self, file_path: str) -> tuple[str, float | None]:
        """Read a source file's full content, cached by mtime (#50 / I1).

        Shared by `_extract_import_context` and `_get_class_signature` so a
        file with N chunks is opened once per index run instead of N times —
        each used to open the same file separately (O(chunks x filesize)).
        Cache key is file_path; invalidated when mtime changes.

        Returns ``(content, mtime)``. Callers that memoize their own derived
        result per file (I2 / I2b) validate against this same mtime, so no
        second ``stat()`` call is needed.

        Raises whatever `open()`/`.read()` raise (OSError, UnicodeDecodeError);
        callers handle those themselves so each keeps its own log message.
        """
        cached_mtime, content = self._class_file_cache.get(file_path, (None, None))
        try:
            current_mtime = Path(file_path).stat().st_mtime
        except OSError:
            current_mtime = None

        if content is None or cached_mtime != current_mtime:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            if current_mtime is not None:
                self._class_file_cache[file_path] = (current_mtime, content)

        return content, current_mtime

    def _extract_import_context(self, file_path: str, max_imports: int = 10) -> str:
        """Extract first N import statements from file header.

        Args:
            file_path: Absolute path to the source file
            max_imports: Maximum number of import lines to extract

        Returns:
            String containing import statements, or empty string if none found
        """
        try:
            content, mtime = self._read_source_cached(file_path)
        except (OSError, UnicodeDecodeError) as e:
            self._logger.debug(
                f"Failed to extract import context from {file_path}: {e}"
            )
            return ""

        # I2: the scan below is identical for every chunk in the same file at
        # the same max_imports setting — memoize it so a file with N chunks
        # scans once instead of N times.
        cached = self._import_ctx_cache.get(file_path)
        if cached is not None and cached[0] == mtime and cached[1] == max_imports:
            return cached[2]

        lines = []
        for line in content.splitlines():
            stripped = line.strip()
            # Collect import statements
            if stripped.startswith(("import ", "from ")):
                lines.append(line.rstrip())
                if len(lines) >= max_imports:
                    break
            # Stop at first non-import, non-comment, non-blank line
            elif (
                stripped
                and not stripped.startswith("#")
                and not stripped.startswith('"""')
                and not stripped.startswith("'''")
            ):
                # Check if we've already collected imports
                if lines:
                    break
                # Otherwise keep scanning (might have docstring before imports)
        result = "\n".join(lines)
        self._import_ctx_cache[file_path] = (mtime, max_imports, result)
        return result

    def _get_class_signature(self, chunk: CodeChunk, max_lines: int = 5) -> str:
        """Extract parent class signature (header + docstring) for method chunks.

        Args:
            chunk: CodeChunk with chunk_type='method' and parent_name set
            max_lines: Maximum number of lines to extract from class definition

        Returns:
            String containing class signature, or empty string if not a method
        """
        # Only applicable to methods
        if chunk.chunk_type != "method" or not chunk.parent_name:
            return ""

        try:
            # Shared with _extract_import_context (#50 / I1): avoids re-reading
            # the same file for every method chunk in it (O(chunks × filesize) → O(files)).
            content, mtime = self._read_source_cached(chunk.file_path)

            # I2b: the regex search + signature extraction below is identical
            # for every sibling method of the same parent class — memoize per
            # (file, parent_name) so N methods do it once instead of N times.
            cache_key = (chunk.file_path, chunk.parent_name)
            cached = self._class_sig_cache.get(cache_key)
            if cached is not None and cached[0] == mtime and cached[1] == max_lines:
                return cached[2]

            # Find class definition containing this method
            # Pattern: "class ClassName" or "class ClassName(BaseClass)"
            class_pattern = rf"^class\s+{re.escape(chunk.parent_name)}\s*[\(:]"

            match = re.search(class_pattern, content, re.MULTILINE)
            if not match:
                self._class_sig_cache[cache_key] = (mtime, max_lines, "")
                return ""

            # Extract class header + first few lines (likely docstring)
            start = match.start()
            lines = content[start:].split("\n")[:max_lines]
            signature = "\n".join(lines).strip()

            # Clean up: if docstring is incomplete, truncate at opening quote
            if '"""' in signature or "'''" in signature:
                # Find first opening quote
                first_quote_idx = min(
                    signature.find('"""') if '"""' in signature else len(signature),
                    signature.find("'''") if "'''" in signature else len(signature),
                )
                # Find matching closing quote
                if '"""' in signature[first_quote_idx:]:
                    close_idx = signature.find('"""', first_quote_idx + 3)
                    if close_idx != -1:
                        signature = signature[: close_idx + 3]
                elif "'''" in signature[first_quote_idx:]:
                    close_idx = signature.find("'''", first_quote_idx + 3)
                    if close_idx != -1:
                        signature = signature[: close_idx + 3]

            self._class_sig_cache[cache_key] = (mtime, max_lines, signature)
            return signature

        except (OSError, UnicodeDecodeError) as e:
            self._logger.debug(
                f"Failed to extract class signature for {chunk.parent_name}: {e}"
            )
            return ""

    def compose(
        self,
        chunk: CodeChunk,
        policy: EmbeddingDocumentPolicy,
        max_chars: int = 6000,
    ) -> str:
        """Assemble the embedding document for one chunk under a given policy.

        Prepends an optional structural header (file path + qualified name),
        optional import context, optional parent-class signature, and the
        chunk's docstring — then the chunk's code content, truncated to fit
        ``max_chars`` when necessary. This is the model-free half of what was
        ``CodeEmbedder.create_embedding_content``; that method now fetches the
        live config, builds the policy, and delegates here.
        """
        # Prepare clean content without fabricated headers
        content_parts = []

        # NEW (v0.9.0): Structural header for module/name/type disambiguation
        if policy.enable_structural_header:
            header_parts = []
            # Add file path for module context
            if hasattr(chunk, "relative_path") and chunk.relative_path:
                header_parts.append(chunk.relative_path)

            # Add chunk type + qualified name (ClassName.method_name or function_name)
            type_name = ""
            if chunk.chunk_type:
                type_name = chunk.chunk_type
            if chunk.parent_name and chunk.name:
                type_name += f" {chunk.parent_name}.{chunk.name}"
            elif chunk.name:
                type_name += f" {chunk.name}"

            if type_name:
                header_parts.append(type_name.strip())

            # Prepend structural header line if any parts exist
            if header_parts:
                content_parts.append(f"# {' | '.join(header_parts)}")

        # NEW: Add import context from file header (if enabled and available)
        if policy.enable_import_context:
            import_context = self._extract_import_context(
                chunk.file_path, max_imports=policy.max_import_lines
            )
            if import_context:
                content_parts.append(f"# Imports:\n{import_context}\n")

        # NEW: Add class context for methods (skeleton approach, if enabled)
        if policy.enable_class_context:
            class_context = self._get_class_signature(
                chunk, max_lines=policy.max_class_signature_lines
            )
            if class_context:
                content_parts.append(f"# Parent class:\n{class_context}\n")

        # Add docstring if available (important context for code understanding)
        docstring_budget = 300
        if chunk.docstring:
            # Keep docstring but limit length to stay within token budget
            docstring = (
                chunk.docstring[:docstring_budget] + "..."
                if len(chunk.docstring) > docstring_budget
                else chunk.docstring
            )
            content_parts.append(f'"""{docstring}"""')

        # Calculate remaining budget for code content
        # Account for import context, class context, and docstring
        context_len = sum(len(part) for part in content_parts)
        remaining_budget = max_chars - context_len - 10  # small buffer

        # Add the actual code content, truncating if necessary
        if len(chunk.content) <= remaining_budget:
            content_parts.append(chunk.content)
        else:
            # Smart truncation: try to keep function signature and important parts
            lines = chunk.content.split("\n")
            if len(lines) > 3:
                # Keep first few lines (signature) and last few lines (return/conclusion)
                head_lines = []
                tail_lines = []
                current_length = context_len

                # Add head lines (function signature, early logic)
                for _i, line in enumerate(lines[: min(len(lines) // 2, 20)]):
                    if current_length + len(line) + 1 > remaining_budget * 0.7:
                        break
                    head_lines.append(line)
                    current_length += len(line) + 1

                # Add tail lines (return statements, conclusions) if space remains
                remaining_space = (
                    remaining_budget - current_length - 20
                )  # buffer for "..."
                for line in reversed(lines[-min(len(lines) // 3, 10) :]):
                    if len("\n".join(tail_lines)) + len(line) + 1 > remaining_space:
                        break
                    tail_lines.insert(0, line)

                if tail_lines:
                    truncated_content = (
                        "\n".join(head_lines)
                        + "\n    # ... (truncated) ...\n"
                        + "\n".join(tail_lines)
                    )
                else:
                    truncated_content = (
                        "\n".join(head_lines) + "\n    # ... (truncated) ..."
                    )
                content_parts.append(truncated_content)
            else:
                # For short chunks, just truncate at character limit
                content_parts.append(
                    chunk.content[:remaining_budget] + "..."
                    if len(chunk.content) > remaining_budget
                    else chunk.content
                )

        return "\n".join(content_parts)
