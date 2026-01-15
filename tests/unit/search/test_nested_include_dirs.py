"""Unit tests for nested include_dirs support (P0 bug fix).

Tests the fix for nested include_dirs patterns like "Scripts/StreamDiffusionTD"
where parent directories need to pass through during traversal to reach the target.
"""

from search.filters import DirectoryFilter, matches_directory_filter


class TestNestedIncludeDirsTraversal:
    """Tests for nested include_dirs support in traversal mode."""

    def test_parent_directory_passes_in_traversal_mode(self):
        """Parent directories pass in traversal mode to allow reaching nested targets."""
        assert (
            matches_directory_filter(
                "Scripts/",
                include_dirs=["Scripts/StreamDiffusionTD/"],
                is_traversal=True,
            )
            is True
        )

    def test_parent_directory_fails_in_strict_mode(self):
        """Parent directories fail in strict mode (file filtering)."""
        assert (
            matches_directory_filter(
                "Scripts/",
                include_dirs=["Scripts/StreamDiffusionTD/"],
                is_traversal=False,
            )
            is False
        )

    def test_target_directory_matches_in_both_modes(self):
        """Target directory itself matches in both traversal and strict modes."""
        assert (
            matches_directory_filter(
                "Scripts/StreamDiffusionTD/",
                include_dirs=["Scripts/StreamDiffusionTD/"],
                is_traversal=True,
            )
            is True
        )
        assert (
            matches_directory_filter(
                "Scripts/StreamDiffusionTD/",
                include_dirs=["Scripts/StreamDiffusionTD/"],
                is_traversal=False,
            )
            is True
        )

    def test_file_inside_target_passes_strict_mode(self):
        """Files inside target directory pass in strict mode."""
        assert (
            matches_directory_filter(
                "Scripts/StreamDiffusionTD/main.py",
                include_dirs=["Scripts/StreamDiffusionTD/"],
                is_traversal=False,
            )
            is True
        )

    def test_sibling_directory_excluded(self):
        """Sibling directories outside include_dirs are excluded."""
        assert (
            matches_directory_filter(
                "Scripts/OtherProject/",
                include_dirs=["Scripts/StreamDiffusionTD/"],
                is_traversal=True,
            )
            is False
        )

    def test_deeply_nested_patterns(self):
        """Deeply nested patterns work correctly at all levels."""
        # All parent directories pass in traversal mode
        assert (
            matches_directory_filter("a/", include_dirs=["a/b/c/d/"], is_traversal=True)
            is True
        )
        assert (
            matches_directory_filter(
                "a/b/", include_dirs=["a/b/c/d/"], is_traversal=True
            )
            is True
        )
        assert (
            matches_directory_filter(
                "a/b/c/", include_dirs=["a/b/c/d/"], is_traversal=True
            )
            is True
        )
        assert (
            matches_directory_filter(
                "a/b/c/d/", include_dirs=["a/b/c/d/"], is_traversal=True
            )
            is True
        )

    def test_multiple_nested_include_dirs(self):
        """Multiple nested include patterns work correctly."""
        include_dirs = ["src/core/", "lib/utils/helpers/"]

        # Parents of first pattern
        assert (
            matches_directory_filter(
                "src/", include_dirs=include_dirs, is_traversal=True
            )
            is True
        )

        # Parents of second pattern
        assert (
            matches_directory_filter(
                "lib/", include_dirs=include_dirs, is_traversal=True
            )
            is True
        )
        assert (
            matches_directory_filter(
                "lib/utils/", include_dirs=include_dirs, is_traversal=True
            )
            is True
        )

        # Unrelated directory excluded
        assert (
            matches_directory_filter(
                "tests/", include_dirs=include_dirs, is_traversal=True
            )
            is False
        )

    def test_path_without_trailing_slash(self):
        """Paths without trailing slashes work correctly (auto-added)."""
        assert (
            matches_directory_filter(
                "Scripts", include_dirs=["Scripts/StreamDiffusionTD"], is_traversal=True
            )
            is True
        )

    def test_backslash_paths_normalized(self):
        """Windows-style backslash paths are normalized."""
        assert (
            matches_directory_filter(
                "Scripts\\",
                include_dirs=["Scripts/StreamDiffusionTD/"],
                is_traversal=True,
            )
            is True
        )


class TestDirectoryFilterHelperMethods:
    """Tests for DirectoryFilter helper methods."""

    def test_matches_for_traversal(self):
        """matches_for_traversal() uses traversal mode."""
        filter_obj = DirectoryFilter(include_dirs=["Scripts/StreamDiffusionTD/"])

        # Parent passes in traversal mode
        assert filter_obj.matches_for_traversal("Scripts/") is True

        # Sibling fails in traversal mode
        assert filter_obj.matches_for_traversal("Other/") is False

    def test_matches_for_file(self):
        """matches_for_file() uses strict mode."""
        filter_obj = DirectoryFilter(include_dirs=["Scripts/StreamDiffusionTD/"])

        # Parent fails in strict mode
        assert filter_obj.matches_for_file("Scripts/") is False

        # File inside target passes in strict mode
        assert filter_obj.matches_for_file("Scripts/StreamDiffusionTD/main.py") is True

    def test_matches_with_explicit_mode(self):
        """matches() respects explicit is_traversal parameter."""
        filter_obj = DirectoryFilter(include_dirs=["Scripts/StreamDiffusionTD/"])

        # Explicit traversal mode
        assert filter_obj.matches("Scripts/", is_traversal=True) is True

        # Explicit strict mode
        assert filter_obj.matches("Scripts/", is_traversal=False) is False


class TestExcludeDirsWithNestedIncludes:
    """Tests for exclude_dirs behavior with nested include_dirs."""

    def test_excluded_sibling_within_parent(self):
        """Excluded siblings don't prevent traversing to included targets."""
        # Scenario: Include Scripts/StreamDiffusionTD, exclude Scripts/tests
        include_dirs = ["Scripts/StreamDiffusionTD/"]
        exclude_dirs = ["Scripts/tests/"]

        # Parent "Scripts/" passes traversal
        assert (
            matches_directory_filter(
                "Scripts/",
                include_dirs=include_dirs,
                exclude_dirs=exclude_dirs,
                is_traversal=True,
            )
            is True
        )

        # Target passes
        assert (
            matches_directory_filter(
                "Scripts/StreamDiffusionTD/",
                include_dirs=include_dirs,
                exclude_dirs=exclude_dirs,
                is_traversal=True,
            )
            is True
        )

        # Excluded sibling fails
        assert (
            matches_directory_filter(
                "Scripts/tests/",
                include_dirs=include_dirs,
                exclude_dirs=exclude_dirs,
                is_traversal=True,
            )
            is False
        )

    def test_file_in_excluded_sibling_fails(self):
        """Files in excluded siblings are correctly filtered."""
        include_dirs = ["Scripts/StreamDiffusionTD/"]
        exclude_dirs = ["Scripts/tests/"]

        # File in excluded directory fails
        assert (
            matches_directory_filter(
                "Scripts/tests/test_main.py",
                include_dirs=include_dirs,
                exclude_dirs=exclude_dirs,
                is_traversal=False,
            )
            is False
        )

        # File in included directory passes
        assert (
            matches_directory_filter(
                "Scripts/StreamDiffusionTD/main.py",
                include_dirs=include_dirs,
                exclude_dirs=exclude_dirs,
                is_traversal=False,
            )
            is True
        )
