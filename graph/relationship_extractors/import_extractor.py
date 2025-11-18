"""
Import Extractor

Extracts "imports" relationships from Python import statements.

Relationship: Module/File -> Imported module/symbol
Example: from module import func  →  current_file --[imports]--> module.func

AST Nodes Used: ast.Import, ast.ImportFrom
Complexity: Medium (handling relative imports, aliases, star imports)
"""

import ast
from typing import Any, Dict, List

from graph.relationship_extractors.base_extractor import BaseRelationshipExtractor
from graph.relationship_types import RelationshipEdge, RelationshipType


class ImportExtractor(BaseRelationshipExtractor):
    """
    Extract import relationships from Python AST.

    Detection Method:
    - Parse ast.Import nodes (import module)
    - Parse ast.ImportFrom nodes (from module import symbol)
    - Handle relative imports (from . import, from .. import)
    - Track import aliases

    Edge Direction:
    - Source: File/module doing the importing
    - Target: Module/symbol being imported

    Confidence Scoring:
    - 1.0: All imports (explicit in code)

    Example AST:
    ```python
    import os
    from typing import List, Dict
    from .local import helper
    ```

    Creates edges:
    - file.py -> os
    - file.py -> typing.List
    - file.py -> typing.Dict
    - file.py -> .local.helper (relative import)
    """

    def __init__(self):
        """Initialize the import extractor."""
        super().__init__()
        self.relationship_type = RelationshipType.IMPORTS

    def extract(
        self, code: str, chunk_metadata: Dict[str, Any]
    ) -> List[RelationshipEdge]:
        """
        Extract import relationships from code.

        Args:
            code: Source code string
            chunk_metadata: Metadata about the code chunk

        Returns:
            List of RelationshipEdge objects for imports
        """
        self._reset_state()

        # Parse code
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            # DEBUG: Method chunks often fail to parse standalone but parent class chunks succeed
            self.logger.debug(
                f"Failed to parse code in {chunk_metadata.get('file_path')}: {e}"
            )
            return []

        # Extract imports
        self._extract_from_tree(tree, chunk_metadata)

        # Log results
        self._log_extraction_result(chunk_metadata)

        return self.edges

    def _extract_from_tree(self, tree: ast.AST, chunk_metadata: Dict[str, Any]) -> None:
        """
        Walk AST and extract import statements.

        Args:
            tree: AST tree
            chunk_metadata: Chunk metadata
        """
        for node in ast.walk(tree):
            # import module
            if isinstance(node, ast.Import):
                self._extract_from_import(node, chunk_metadata)

            # from module import symbol
            elif isinstance(node, ast.ImportFrom):
                self._extract_from_import_from(node, chunk_metadata)

    def _extract_from_import(
        self, import_node: ast.Import, chunk_metadata: Dict[str, Any]
    ) -> None:
        """
        Extract from import statement.

        Example:
            import os
            import sys as system
            import package.submodule

        Args:
            import_node: ast.Import node
            chunk_metadata: Chunk metadata
        """
        source_id = chunk_metadata.get("chunk_id")
        line_number = import_node.lineno

        for alias in import_node.names:
            module_name = alias.name
            alias_name = alias.asname  # None if no alias

            # Skip stdlib if desired (we'll keep them for now)
            # if self._should_skip_target(module_name, include_stdlib=False):
            #     continue

            # Create import edge
            self._add_edge(
                source_id=source_id,
                target_name=module_name,
                line_number=line_number,
                confidence=1.0,
                import_type="import",
                alias=alias_name,
            )

    def _extract_from_import_from(
        self, import_node: ast.ImportFrom, chunk_metadata: Dict[str, Any]
    ) -> None:
        """
        Extract from "from module import symbol" statement.

        Examples:
            from os import path
            from typing import List, Dict
            from . import helper
            from ..package import module

        Args:
            import_node: ast.ImportFrom node
            chunk_metadata: Chunk metadata
        """
        source_id = chunk_metadata.get("chunk_id")
        line_number = import_node.lineno

        # Get module name (may be None for relative imports)
        module_name = import_node.module or ""

        # Handle relative imports (. or ..)
        relative_prefix = "." * import_node.level if import_node.level else ""

        # Build full module path
        if relative_prefix and module_name:
            full_module = f"{relative_prefix}{module_name}"
        elif relative_prefix:
            full_module = relative_prefix
        else:
            full_module = module_name

        # Extract imported symbols
        for alias in import_node.names:
            symbol_name = alias.name
            alias_name = alias.asname

            # Handle star import
            if symbol_name == "*":
                # Star import: from module import *
                target_name = f"{full_module}.*" if full_module else "*"
                is_star_import = True
            else:
                # Regular import: from module import symbol
                if full_module and not module_name:
                    # Pure relative import: from . import helper → .helper
                    target_name = f"{relative_prefix}{symbol_name}"
                elif full_module:
                    # Module import: from module import symbol → module.symbol
                    target_name = f"{full_module}.{symbol_name}"
                else:
                    target_name = symbol_name
                is_star_import = False

            # Skip stdlib if desired (we'll keep them for now)
            # if self._should_skip_target(target_name, include_stdlib=False):
            #     continue

            # Create import edge
            self._add_edge(
                source_id=source_id,
                target_name=target_name,
                line_number=line_number,
                confidence=1.0,
                import_type="from_import",
                module=full_module,
                symbol=symbol_name,
                alias=alias_name,
                is_star_import=is_star_import,
                is_relative=import_node.level > 0,
                relative_level=import_node.level,
            )

    def _get_canonical_module_name(self, module_name: str, file_path: str) -> str:
        """
        Convert module name to canonical form.

        For relative imports, try to resolve to absolute path based on file location.

        Args:
            module_name: Module name (may have . prefix)
            file_path: Path to current file

        Returns:
            Canonical module name

        Example:
            If file is "project/subpackage/file.py":
            - ".helper" -> "project.subpackage.helper"
            - "..util" -> "project.util"
        """
        # For now, just return module_name as-is
        # Full resolution would require package structure knowledge
        return module_name


# ===== Convenience Functions =====


def extract_import_relationships(
    code: str, file_path: str = "unknown.py"
) -> List[RelationshipEdge]:
    """
    Convenience function to extract import relationships.

    Args:
        code: Python source code
        file_path: Path to file (for chunk ID)

    Returns:
        List of import edges

    Example:
        >>> code = '''
        ... import os
        ... from typing import List, Dict
        ... from .local import helper
        ... '''
        >>> edges = extract_import_relationships(code)
        >>> len(edges) >= 3
        True
        >>> import_targets = {e.target_name for e in edges}
        >>> 'os' in import_targets
        True
    """
    extractor = ImportExtractor()
    chunk_metadata = {
        "chunk_id": f"{file_path}:0-0:module:module",
        "file_path": file_path,
        "name": "module",
        "chunk_type": "module",
    }

    return extractor.extract(code, chunk_metadata)
