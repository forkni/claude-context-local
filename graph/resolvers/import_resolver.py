"""
Import resolution for call graph extraction.

Extracts and resolves import statements to enable accurate type resolution
for aliased imports (e.g., from x import Y as Z; Z.method() -> Y.method).
"""

import ast
import logging


logger = logging.getLogger(__name__)


class ImportResolver:
    """
    Resolves import statements from Python source files.

    Handles:
    - import os                    -> {"os": "os"}
    - import os.path               -> {"os": "os.path"}
    - from x import Y              -> {"Y": "x.Y"}
    - from x import Y as Z         -> {"Z": "x.Y"}
    - from . import helper         -> {"helper": ".helper"}
    - from ..utils import Parser   -> {"Parser": "..utils.Parser"}
    - from x import *              -> {}  (cannot resolve)

    Includes caching for file-level imports to avoid repeated file reads.
    """

    def __init__(self) -> None:
        """Initialize the import resolver with an empty cache."""
        self._file_imports_cache: dict[str, dict[str, str]] = {}

    def clear_cache(self) -> None:
        """Clear the file imports cache."""
        self._file_imports_cache.clear()

    def extract_imports(self, tree: ast.AST) -> dict[str, str]:
        """
        Extract import mappings from an AST.

        Args:
            tree: AST tree to analyze

        Returns:
            Dictionary mapping imported names/aliases to qualified names
        """
        imports: dict[str, str] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # import os, import os.path, import x as y
                for alias in node.names:
                    # Use alias if provided, otherwise first component
                    local_name = (
                        alias.asname if alias.asname else alias.name.split(".")[0]
                    )
                    imports[local_name] = alias.name

            elif isinstance(node, ast.ImportFrom):
                # from x import Y, from x import Y as Z
                module = node.module or ""
                # Handle relative imports: from . import x, from .. import y
                prefix = "." * node.level if node.level else ""
                full_module = f"{prefix}{module}" if module else prefix

                for alias in node.names:
                    if alias.name == "*":
                        # Star import - cannot resolve specific names
                        logger.debug(
                            f"Star import from '{full_module}' cannot be resolved"
                        )
                        continue

                    local_name = alias.asname if alias.asname else alias.name
                    # Build qualified name
                    if module:
                        # Has module name: from .utils import Parser -> .utils.Parser
                        qualified = f"{full_module}.{alias.name}"
                    elif prefix:
                        # Pure relative: from . import helper -> .helper
                        qualified = f"{prefix}{alias.name}"
                    else:
                        # Absolute: from package import Class -> package.Class
                        qualified = alias.name
                    imports[local_name] = qualified

        return imports

    def read_file_imports(self, file_path: str) -> dict[str, str]:
        """
        Read and extract imports from a full file.

        This method reads the entire file (not just the chunk code) to extract
        all import statements, enabling resolution of types used in method chunks.

        Results are cached to avoid repeated file reads.

        Args:
            file_path: Path to the source file

        Returns:
            Dictionary mapping imported names to qualified names,
            or empty dict if file cannot be read
        """
        # Check cache first
        if file_path in self._file_imports_cache:
            return self._file_imports_cache[file_path]

        imports: dict[str, str] = {}

        if not file_path:
            return imports

        try:
            with open(file_path, encoding="utf-8") as f:
                file_content = f.read()

            tree = ast.parse(file_content)
            imports = self.extract_imports(tree)

            # Cache the result
            self._file_imports_cache[file_path] = imports

        except (OSError, SyntaxError) as e:
            logger.debug(f"Could not read imports from {file_path}: {e}")
            # Cache empty result to avoid repeated failures
            self._file_imports_cache[file_path] = {}

        return imports
