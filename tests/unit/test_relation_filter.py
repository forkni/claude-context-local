"""Unit tests for RepositoryRelationFilter.

Tests import classification for stdlib, third-party, and local modules.
"""

import sys

from graph.relation_filter import RepositoryRelationFilter


class TestRelationFilter:
    """Test import classification."""

    def test_stdlib_detection(self):
        """Standard library modules should be classified correctly."""
        filter = RepositoryRelationFilter()

        # Common stdlib modules
        assert filter.classify_import("os") == "stdlib"
        assert filter.classify_import("os.path") == "stdlib"
        assert filter.classify_import("json") == "stdlib"
        assert filter.classify_import("asyncio") == "stdlib"
        assert filter.classify_import("pathlib") == "stdlib"
        assert filter.classify_import("typing") == "stdlib"
        assert filter.classify_import("logging") == "stdlib"

    def test_relative_import_is_local(self):
        """Relative imports should be classified as local."""
        filter = RepositoryRelationFilter()

        assert filter.classify_import(".module") == "local"
        assert filter.classify_import("..package.module") == "local"
        assert filter.classify_import(".") == "local"
        assert filter.classify_import("..") == "local"

    def test_third_party_detection(self):
        """Unknown modules should be classified as third-party."""
        filter = RepositoryRelationFilter()

        # These aren't in stdlib or project
        assert filter.classify_import("numpy") == "third_party"
        assert filter.classify_import("torch") == "third_party"
        assert filter.classify_import("requests") == "third_party"
        assert filter.classify_import("fastapi") == "third_party"
        assert filter.classify_import("networkx") == "third_party"

    def test_builtin_detection(self):
        """Built-in functions should be classified as builtin."""
        filter = RepositoryRelationFilter()

        assert filter.classify_import("str") == "builtin"
        assert filter.classify_import("int") == "builtin"
        assert filter.classify_import("list") == "builtin"
        assert filter.classify_import("dict") == "builtin"

    def test_project_module_detection(self, tmp_path):
        """Project modules should be detected from directory structure."""
        # Create fake project structure
        (tmp_path / "search").mkdir()
        (tmp_path / "search" / "__init__.py").touch()
        (tmp_path / "search" / "indexer.py").touch()

        (tmp_path / "graph").mkdir()
        (tmp_path / "graph" / "__init__.py").touch()
        (tmp_path / "graph" / "graph_storage.py").touch()

        filter = RepositoryRelationFilter(project_root=tmp_path)

        assert filter.classify_import("search") == "local"
        assert filter.classify_import("search.indexer") == "local"
        assert filter.classify_import("graph") == "local"
        assert filter.classify_import("graph.graph_storage") == "local"

    def test_empty_module_name(self):
        """Empty module name should return unknown."""
        filter = RepositoryRelationFilter()

        assert filter.classify_import("") == "unknown"
        assert filter.classify_import(None) == "unknown"

    def test_python_310_required(self):
        """Verify sys.stdlib_module_names is available."""
        assert hasattr(
            sys, "stdlib_module_names"
        ), "Python 3.10+ required for sys.stdlib_module_names"

    def test_is_project_internal(self, tmp_path):
        """Test is_project_internal helper method."""
        (tmp_path / "myproject").mkdir()
        (tmp_path / "myproject" / "__init__.py").touch()

        filter = RepositoryRelationFilter(project_root=tmp_path)

        # Local modules are project-internal
        assert filter.is_project_internal("myproject")
        assert filter.is_project_internal(".relative")

        # Builtins are considered project-internal
        assert filter.is_project_internal("str")

        # Stdlib is NOT project-internal
        assert not filter.is_project_internal("os")
        assert not filter.is_project_internal("json")

        # Third-party is NOT project-internal
        assert not filter.is_project_internal("numpy")
        assert not filter.is_project_internal("torch")

    def test_should_include_in_graph_defaults(self):
        """Test should_include_in_graph with default settings."""
        filter = RepositoryRelationFilter()

        # Local always included
        assert filter.should_include_in_graph(".relative")

        # Stdlib excluded by default
        assert not filter.should_include_in_graph("os")
        assert not filter.should_include_in_graph("json")

        # Third-party excluded by default
        assert not filter.should_include_in_graph("numpy")
        assert not filter.should_include_in_graph("torch")

    def test_should_include_in_graph_with_stdlib(self):
        """Test should_include_in_graph with stdlib enabled."""
        filter = RepositoryRelationFilter()

        # Stdlib included when enabled
        assert filter.should_include_in_graph("os", include_stdlib=True)
        assert filter.should_include_in_graph("json", include_stdlib=True)

        # Third-party still excluded
        assert not filter.should_include_in_graph("numpy", include_stdlib=True)

    def test_should_include_in_graph_with_third_party(self):
        """Test should_include_in_graph with third-party enabled."""
        filter = RepositoryRelationFilter()

        # Third-party included when enabled
        assert filter.should_include_in_graph("numpy", include_third_party=True)
        assert filter.should_include_in_graph("torch", include_third_party=True)

        # Stdlib still excluded
        assert not filter.should_include_in_graph("os", include_third_party=True)

    def test_should_include_in_graph_all_enabled(self):
        """Test should_include_in_graph with all categories enabled."""
        filter = RepositoryRelationFilter()

        # All imports included
        assert filter.should_include_in_graph(
            "os", include_stdlib=True, include_third_party=True
        )
        assert filter.should_include_in_graph(
            "numpy", include_stdlib=True, include_third_party=True
        )
        assert filter.should_include_in_graph(
            ".relative", include_stdlib=True, include_third_party=True
        )


class TestGraphSizeReduction:
    """Benchmark graph edge count reduction."""

    def test_graph_edge_reduction_placeholder(self):
        """Placeholder for graph edge reduction benchmarking.

        This test will measure actual reduction after indexing a real project.
        Expected: 30-50% reduction in edge count when filtering stdlib/third-party.
        """
        # This will be implemented after full integration
        # Requires indexing a project with the new filtering enabled
        pass
