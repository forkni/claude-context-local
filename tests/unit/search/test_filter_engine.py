"""Unit tests for FilterEngine and FilterCriteria classes.

Tests the unified filter engine that consolidates filter logic from
CodeIndexManager and HybridSearcher.
"""

from search.filters import FilterCriteria, FilterEngine


class TestFilterCriteria:
    """Tests for FilterCriteria dataclass and from_dict factory."""

    def test_from_dict_all_fields(self):
        """Test creating FilterCriteria with all fields specified."""
        filters = {
            "include_dirs": ["src/"],
            "exclude_dirs": ["tests/"],
            "file_pattern": "utils",
            "chunk_type": "function",
            "tags": ["python", "util"],
            "folder_structure": ["src", "utils"],
            "custom_field": "custom_value",
        }

        criteria = FilterCriteria.from_dict(filters)

        assert criteria.include_dirs == ["src/"]
        assert criteria.exclude_dirs == ["tests/"]
        assert criteria.file_pattern == ["utils"]  # Normalized to list
        assert criteria.chunk_type == "function"
        assert criteria.tags == {"python", "util"}  # Normalized to set
        assert criteria.folder_structure == {"src", "utils"}  # Normalized to set
        assert criteria.extra_filters == {"custom_field": "custom_value"}

    def test_from_dict_partial(self):
        """Test creating FilterCriteria with only some fields."""
        filters = {
            "chunk_type": "class",
            "include_dirs": ["src/", "lib/"],
        }

        criteria = FilterCriteria.from_dict(filters)

        assert criteria.include_dirs == ["src/", "lib/"]
        assert criteria.chunk_type == "class"
        assert criteria.exclude_dirs is None
        assert criteria.file_pattern is None
        assert criteria.tags is None
        assert criteria.folder_structure is None
        assert criteria.extra_filters is None

    def test_from_dict_empty(self):
        """Test creating FilterCriteria from empty dict."""
        criteria = FilterCriteria.from_dict({})

        assert criteria.include_dirs is None
        assert criteria.exclude_dirs is None
        assert criteria.file_pattern is None
        assert criteria.chunk_type is None
        assert criteria.tags is None
        assert criteria.folder_structure is None
        assert criteria.extra_filters is None

    def test_file_pattern_normalization_string(self):
        """Test file_pattern is normalized to list from string."""
        criteria = FilterCriteria.from_dict({"file_pattern": "utils"})
        assert criteria.file_pattern == ["utils"]

    def test_file_pattern_normalization_list(self):
        """Test file_pattern stays as list."""
        criteria = FilterCriteria.from_dict({"file_pattern": ["utils", "helpers"]})
        assert criteria.file_pattern == ["utils", "helpers"]

    def test_tags_normalization(self):
        """Test tags are normalized to set."""
        criteria = FilterCriteria.from_dict({"tags": ["python", "util", "python"]})
        assert criteria.tags == {"python", "util"}

    def test_folder_structure_normalization(self):
        """Test folder_structure is normalized to set."""
        criteria = FilterCriteria.from_dict({"folder_structure": ["src", "utils"]})
        assert criteria.folder_structure == {"src", "utils"}


class TestFilterEngine:
    """Tests for FilterEngine filtering logic."""

    def test_matches_directory_filter_include(self):
        """Test directory inclusion filter."""
        engine = FilterEngine.from_dict({"include_dirs": ["src/"]})

        assert engine.matches({"relative_path": "src/main.py"}) is True
        assert engine.matches({"relative_path": "tests/test_main.py"}) is False

    def test_matches_directory_filter_exclude(self):
        """Test directory exclusion filter."""
        engine = FilterEngine.from_dict({"exclude_dirs": ["tests/"]})

        assert engine.matches({"relative_path": "src/main.py"}) is True
        assert engine.matches({"relative_path": "tests/test_main.py"}) is False

    def test_matches_directory_filter_both(self):
        """Test combined include and exclude filters."""
        engine = FilterEngine.from_dict(
            {"include_dirs": ["src/"], "exclude_dirs": ["src/vendor/"]}
        )

        assert engine.matches({"relative_path": "src/main.py"}) is True
        assert engine.matches({"relative_path": "src/vendor/lib.py"}) is False
        assert engine.matches({"relative_path": "tests/test_main.py"}) is False

    def test_matches_file_pattern_single(self):
        """Test file pattern matching with single pattern."""
        engine = FilterEngine.from_dict({"file_pattern": "utils"})

        assert engine.matches({"relative_path": "src/utils.py"}) is True
        assert engine.matches({"relative_path": "src/utils/helpers.py"}) is True
        assert engine.matches({"relative_path": "src/main.py"}) is False

    def test_matches_file_pattern_multiple(self):
        """Test file pattern matching with multiple patterns."""
        engine = FilterEngine.from_dict({"file_pattern": ["utils", "helpers"]})

        assert engine.matches({"relative_path": "src/utils.py"}) is True
        assert engine.matches({"relative_path": "src/helpers.py"}) is True
        assert engine.matches({"relative_path": "src/main.py"}) is False

    def test_matches_chunk_type(self):
        """Test chunk type exact matching."""
        engine = FilterEngine.from_dict({"chunk_type": "function"})

        assert engine.matches({"chunk_type": "function"}) is True
        assert engine.matches({"chunk_type": "class"}) is False
        assert engine.matches({}) is False

    def test_matches_tags_intersection(self):
        """Test tag intersection matching."""
        engine = FilterEngine.from_dict({"tags": ["python", "util"]})

        # Must have at least one overlapping tag
        assert engine.matches({"tags": ["python", "core"]}) is True
        assert engine.matches({"tags": ["util"]}) is True
        assert engine.matches({"tags": ["javascript"]}) is False
        assert engine.matches({"tags": []}) is False

    def test_matches_folder_structure(self):
        """Test folder structure intersection matching."""
        engine = FilterEngine.from_dict({"folder_structure": ["src", "utils"]})

        # Must have at least one overlapping folder
        assert engine.matches({"folder_structure": ["src", "core"]}) is True
        assert engine.matches({"folder_structure": ["utils"]}) is True
        assert engine.matches({"folder_structure": ["tests"]}) is False
        assert engine.matches({"folder_structure": []}) is False

    def test_matches_extra_filters(self):
        """Test generic metadata key matching."""
        engine = FilterEngine.from_dict({"project": "my-project", "version": "1.0"})

        assert engine.matches({"project": "my-project", "version": "1.0"}) is True
        assert engine.matches({"project": "my-project", "version": "2.0"}) is False
        assert engine.matches({"project": "other-project", "version": "1.0"}) is False

    def test_matches_combined_filters(self):
        """Test multiple filters combined."""
        engine = FilterEngine.from_dict(
            {
                "include_dirs": ["src/"],
                "chunk_type": "function",
                "file_pattern": "utils",
                "tags": ["python"],
            }
        )

        # All filters must pass
        assert (
            engine.matches(
                {
                    "relative_path": "src/utils.py",
                    "chunk_type": "function",
                    "tags": ["python", "util"],
                }
            )
            is True
        )

        # Fail on chunk_type mismatch
        assert (
            engine.matches(
                {
                    "relative_path": "src/utils.py",
                    "chunk_type": "class",
                    "tags": ["python"],
                }
            )
            is False
        )

        # Fail on directory mismatch
        assert (
            engine.matches(
                {
                    "relative_path": "tests/utils.py",
                    "chunk_type": "function",
                    "tags": ["python"],
                }
            )
            is False
        )

    def test_matches_no_filters(self):
        """Test that no filters means all metadata matches."""
        engine = FilterEngine.from_dict({})

        assert engine.matches({"anything": "value"}) is True
        assert engine.matches({}) is True

    def test_filter_results(self):
        """Test filtering a list of results."""
        engine = FilterEngine.from_dict(
            {"chunk_type": "function", "include_dirs": ["src/"]}
        )

        results = [
            {"metadata": {"chunk_type": "function", "relative_path": "src/main.py"}},
            {"metadata": {"chunk_type": "class", "relative_path": "src/main.py"}},
            {"metadata": {"chunk_type": "function", "relative_path": "tests/test.py"}},
            {"metadata": {"chunk_type": "function", "relative_path": "src/utils.py"}},
        ]

        filtered = engine.filter_results(results)

        assert len(filtered) == 2
        assert filtered[0]["metadata"]["relative_path"] == "src/main.py"
        assert filtered[1]["metadata"]["relative_path"] == "src/utils.py"

    def test_filter_results_custom_metadata_key(self):
        """Test filtering with custom metadata key."""
        engine = FilterEngine.from_dict({"chunk_type": "function"})

        results = [
            {"data": {"chunk_type": "function"}},
            {"data": {"chunk_type": "class"}},
        ]

        filtered = engine.filter_results(results, metadata_key="data")

        assert len(filtered) == 1
        assert filtered[0]["data"]["chunk_type"] == "function"

    def test_filter_results_empty(self):
        """Test filtering empty results list."""
        engine = FilterEngine.from_dict({"chunk_type": "function"})

        assert engine.filter_results([]) == []

    def test_from_dict_factory(self):
        """Test from_dict factory method creates working engine."""
        filters = {"include_dirs": ["src/"], "chunk_type": "function"}

        engine = FilterEngine.from_dict(filters)

        assert isinstance(engine, FilterEngine)
        assert isinstance(engine.criteria, FilterCriteria)
        assert engine.criteria.include_dirs == ["src/"]
        assert engine.criteria.chunk_type == "function"
