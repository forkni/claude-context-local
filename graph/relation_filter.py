"""Repository-dependent relation filtering for RepoGraph-style noise reduction.

This module implements Project-Dependent Relation Filtering from the RepoGraph paper
(ICLR 2025) to filter out stdlib and third-party imports, focusing graph traversal
on project-internal code.
"""

import sys
from pathlib import Path


class RepositoryRelationFilter:
    """Classifies imports as stdlib, third-party, or local (project-internal).

    Implements Project-Dependent Relation Filtering from RepoGraph (ICLR 2025).
    This helps clean up the code graph by filtering out noise from standard library
    and third-party packages, making ego-graph neighbors more relevant.
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize filter with project context.

        Args:
            project_root: Root directory of the project being indexed.
                          Used to detect local modules.
        """
        self.project_root = Path(project_root) if project_root else None
        self.project_modules: set[str] = set()
        self._stdlib_modules: set[str] | None = None

        if self.project_root:
            self._discover_project_modules()

    def _discover_project_modules(self) -> None:
        """Discover all Python modules in the project."""
        if not self.project_root or not self.project_root.exists():
            return

        for py_file in self.project_root.rglob("*.py"):
            # Convert path to module name
            rel_path = py_file.relative_to(self.project_root)
            parts = list(rel_path.parts)

            # Remove .py extension from last part
            if parts[-1].endswith(".py"):
                parts[-1] = parts[-1][:-3]

            # Add all possible module paths
            # e.g., search/indexer.py -> ["search", "search.indexer"]
            for i in range(len(parts)):
                module_name = ".".join(parts[: i + 1])
                if module_name and module_name != "__init__":
                    self.project_modules.add(module_name)

    @property
    def stdlib_modules(self) -> set[str]:
        """Get stdlib modules using sys.stdlib_module_names (Python 3.10+)."""
        if self._stdlib_modules is None:
            # Requires Python 3.10+ (project requirement)
            self._stdlib_modules = set(sys.stdlib_module_names)
        return self._stdlib_modules

    def classify_import(self, module_name: str) -> str:
        """Classify import as 'stdlib', 'third_party', or 'local'.

        Args:
            module_name: Full module name (e.g., "os.path", "numpy.array")

        Returns:
            One of: "stdlib", "third_party", "local", "builtin", "unknown"
        """
        if not module_name:
            return "unknown"

        # Handle relative imports
        if module_name.startswith("."):
            return "local"

        # Get top-level module name
        top_level = module_name.split(".")[0]

        # Check builtins
        import builtins

        if hasattr(builtins, top_level):
            return "builtin"

        # Check stdlib
        if top_level in self.stdlib_modules:
            return "stdlib"

        # Check project-local
        if top_level in self.project_modules:
            return "local"

        # Default to third-party (pip-installed packages)
        return "third_party"

    def is_project_internal(self, module_name: str) -> bool:
        """Check if import is project-internal (not stdlib/third-party).

        Args:
            module_name: The module being imported

        Returns:
            True if import is local or builtin, False otherwise
        """
        category = self.classify_import(module_name)
        return category in ("local", "builtin")

    def should_include_in_graph(
        self,
        module_name: str,
        include_stdlib: bool = False,
        include_third_party: bool = False,
    ) -> bool:
        """Determine if import should be included in graph traversal.

        Args:
            module_name: The module being imported
            include_stdlib: Include standard library imports
            include_third_party: Include third-party package imports

        Returns:
            True if import should be included in graph
        """
        category = self.classify_import(module_name)

        if category == "local":
            return True
        if category == "stdlib":
            return include_stdlib
        if category == "third_party":
            return include_third_party
        if category == "builtin":
            return include_stdlib  # Treat builtins like stdlib

        return False  # Unknown - exclude by default
